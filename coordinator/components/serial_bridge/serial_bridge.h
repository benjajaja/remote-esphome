#pragma once

#include "esphome/core/component.h"
#include "esphome/core/log.h"
#include "esphome/components/uart/uart.h"
#include "esphome/components/wifi/wifi_component.h"

#ifdef USE_ESP32
#include "lwip/sockets.h"
#include "lwip/netdb.h"
#endif

namespace esphome {
namespace serial_bridge {

class SerialBridge : public Component {
 public:
  void set_uart_parent(uart::UARTComponent *parent) { this->uart_ = parent; }
  void set_port(uint16_t port) { this->port_ = port; }
  void setup() override;
  void loop() override;
  float get_setup_priority() const override { return setup_priority::AFTER_WIFI; }

 protected:
  uart::UARTComponent *uart_;
  uint16_t port_ = 8888;
  bool server_started_ = false;
#ifdef USE_ESP32
  int server_socket_ = -1;
  int client_socket_ = -1;
#endif
};

}  // namespace serial_bridge
}  // namespace esphome
