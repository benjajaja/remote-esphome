#include "serial_bridge.h"

#ifdef USE_ESP32
#include "lwip/sockets.h"
#include "lwip/netdb.h"
#include "fcntl.h"
#include "errno.h"
#endif

namespace esphome {
namespace serial_bridge {

static const char *TAG = "serial_bridge";

void SerialBridge::setup() {
  ESP_LOGI(TAG, "Serial bridge component ready, will start server when WiFi connects");
}

void SerialBridge::loop() {
#ifdef USE_ESP32
  // Check if WiFi is connected and server needs to be started
  if (!this->server_started_ && wifi::global_wifi_component->is_connected()) {
    // Create socket
    this->server_socket_ = socket(AF_INET, SOCK_STREAM, 0);
    if (this->server_socket_ < 0) {
      ESP_LOGE(TAG, "Failed to create socket");
      return;
    }

    // Set socket options
    int opt = 1;
    setsockopt(this->server_socket_, SOL_SOCKET, SO_REUSEADDR, &opt, sizeof(opt));

    // Bind socket
    struct sockaddr_in server_addr;
    server_addr.sin_family = AF_INET;
    server_addr.sin_addr.s_addr = INADDR_ANY;
    server_addr.sin_port = htons(this->port_);

    if (bind(this->server_socket_, (struct sockaddr *)&server_addr, sizeof(server_addr)) < 0) {
      ESP_LOGE(TAG, "Failed to bind socket to port %d", this->port_);
      close(this->server_socket_);
      this->server_socket_ = -1;
      return;
    }

    // Listen
    if (listen(this->server_socket_, 1) < 0) {
      ESP_LOGE(TAG, "Failed to listen on socket");
      close(this->server_socket_);
      this->server_socket_ = -1;
      return;
    }

    // Set non-blocking
    fcntl(this->server_socket_, F_SETFL, O_NONBLOCK);

    this->server_started_ = true;
    ESP_LOGI(TAG, "TCP server started on port %d", this->port_);
  }

  // Only proceed if server is started and WiFi is still connected
  if (!this->server_started_ || !wifi::global_wifi_component->is_connected()) {
    return;
  }

  // Accept new connections
  if (this->client_socket_ < 0) {
    struct sockaddr_in client_addr;
    socklen_t client_len = sizeof(client_addr);
    int new_client = accept(this->server_socket_, (struct sockaddr *)&client_addr, &client_len);
    
    if (new_client >= 0) {
      this->client_socket_ = new_client;
      fcntl(this->client_socket_, F_SETFL, O_NONBLOCK);
      ESP_LOGI(TAG, "Client connected");
    }
  }

  if (this->client_socket_ >= 0) {
    // Forward UART -> TCP
    if (this->uart_) {
      while (this->uart_->available()) {
        uint8_t data;
        if (this->uart_->read_byte(&data)) {
          if (send(this->client_socket_, &data, 1, 0) < 0) {
            if (errno != EAGAIN && errno != EWOULDBLOCK) {
              ESP_LOGD(TAG, "Client disconnected (send failed)");
              close(this->client_socket_);
              this->client_socket_ = -1;
              break;
            }
          }
        }
      }
    }

    // Forward TCP -> UART
    uint8_t buffer[64];
    int bytes_received = recv(this->client_socket_, buffer, sizeof(buffer), 0);
    if (bytes_received > 0) {
      for (int i = 0; i < bytes_received; i++) {
        if (this->uart_) {
          this->uart_->write_byte(buffer[i]);
        }
      }
    } else if (bytes_received == 0) {
      ESP_LOGI(TAG, "Client disconnected");
      close(this->client_socket_);
      this->client_socket_ = -1;
    } else if (errno != EAGAIN && errno != EWOULDBLOCK) {
      ESP_LOGW(TAG, "Recv error, closing client");
      close(this->client_socket_);
      this->client_socket_ = -1;
    }
  }
#endif
}

}  // namespace serial_bridge
}  // namespace esphome
