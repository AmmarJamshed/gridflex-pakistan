# Future integration architecture

Initial release uses **Simulation Mode** meters. The same domain model supports later adapters:

| Asset | Adapter target | Platform entity |
|-------|----------------|-----------------|
| Smart meters | DLMS/COSEM, AMI utility APIs | `meters` / `meter_readings` |
| Solar inverters | Modbus / vendor cloud | `participants.solar_kw` + readings |
| Battery BMS | Modbus / REST | `battery_kwh`, `battery_soc` |
| EV chargers | OCPP | shiftable load schedules |
| Building BMS | BACnet / MQTT | curtailable HVAC |
| Industrial PLC | OPC-UA | process windows |
| DISCO / NTDC | Utility APIs | feeder loading, DR signals |

Blockchain remains optional: `market_transactions.blockchain_hash` can later be replaced by a real ledger write without changing settlement math.