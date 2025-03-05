# Module lutron-bacnet 

This is a Viam module to support discovery, management, and control of Lutron devices over the [BACnet protocol](https://en.wikipedia.org/wiki/BACnet).

It exposes devices made up of areas or individual rooms of lights, occupancy & lux sensors, and various automation settings as sensor components on a Viam machine.

## Model hipsterbrown:lutron-bacnet:discover-devices

This service queries the local network of the machine to find available BACnet networks along with their associated devices and properties, i.e. lighting level, occupany, and automation settings.

The output from this discovery can be used to configure a `hipsterbrown:lutron-bacnet:lutron-sensor` component for each device on the available networks.

**It can take a minute or two to return values from the initial discovery, depending on the size of the available networks.**

### Configuration
The following attribute template can be used to configure this model:

```json
{
}
```

#### Attributes

The following attributes are available for this model:

| Name          | Type   | Inclusion | Description                |
|---------------|--------|-----------|----------------------------|

#### Example Configuration

```json
{
}
```


## Model hipsterbrown:lutron-bacnet:lutron-sensor

This sensor composes a BACnet "device" which references an area or individual room of lights, occupancy & lux sensors, and various automation settings known as "objects".
Use the associated `hipsterbrown:lutron-bacnet:discover-devices` to create the necessary configuration for each device on the network.

### Configuration
The following attribute template can be used to configure this model:

```json
{
"address": <string>,
"vendor": <string>,
"objects": []<{
    "address": <string>,
    "name": <string>,
    "type": <"analog-value" | "binary-value" | "multi-state-value">
    }>
}
```

#### Attributes

The following attributes are available for this model:

| Name          | Type   | Inclusion | Description                |
|---------------|--------|-----------|----------------------------|
| `address` | string  | Required  | BACnet address of the device on the network, may be an IP address or network ID. |
| `vendor` | string | Optional  | Device vendor name. This can be helpful metadata when viewing many devices at once. |
| `objects` | array of objects | Optional  | The list of device property objects to read and write from this sensor. |

**Property objects:**

| Name          | Type   | Inclusion | Description                |
|---------------|--------|-----------|----------------------------|
| `address` | string  | Required  | Object ID of the property on the device. |
| `type` | string | Required  | May be one of the following values: "analog-value", "binary-value", "multi-state-value" |
| `name` | string | Optional  | The name of the control provided by this property. Can be used to update properties in a DoCommand. |

#### Example Configuration

```json
{
  "vendor": "Lutron Electronics Co., Inc.",
  "address": "1:0x00000035b9f6",
  "objects": [
    {
      "address": "2",
      "name": "Lighting Level",
      "type": "analog-value"
    }
  ]
}
```

### DoCommand

This component accepts an `update` command to change the present value of a object property on the device. The `value` argument depends on the `type` of the property:

- `analog-value` accepts 0 - 100
- `binary-value` accepts 0 or 1
- `multi-state-value` accepts a number referencing a valid state between 1 and X (where X is the number of available states), this is dependent upon the individual property 

#### Example update

```json
{
  "update": {
    "name": "Lighting Level",
    "value": 50
  }
}
```

```json
{
  "update": {
    "address": "2",
    "value": 50
  }
}
```
