import esphome.codegen as cg
import esphome.config_validation as cv
from esphome.const import CONF_ID
from esphome.components import uart

DEPENDENCIES = ['wifi', 'uart']

serial_bridge_ns = cg.esphome_ns.namespace('serial_bridge')
SerialBridge = serial_bridge_ns.class_('SerialBridge', cg.Component)

CONF_UART_ID = "uart_id"
CONF_PORT = "port"

CONFIG_SCHEMA = cv.Schema({
    cv.GenerateID(): cv.declare_id(SerialBridge),
    cv.Required(CONF_UART_ID): cv.use_id(uart.UARTComponent),
    cv.Optional(CONF_PORT, default=8888): cv.port,
}).extend(cv.COMPONENT_SCHEMA)

async def to_code(config):
    var = cg.new_Pvariable(config[CONF_ID])
    await cg.register_component(var, config)
    
    uart_var = await cg.get_variable(config[CONF_UART_ID])
    cg.add(var.set_uart_parent(uart_var))
    cg.add(var.set_port(config[CONF_PORT]))
