# Juwel HeliaLux Smart Controller

This is a custom component for [Home Assistant](https://www.home-assistant.io/) that creates sensors to show details about your [Juwel HeliaLux Smart Controller](https://www.juwel-aquarium.co.uk/Products/Lighting/LED/HeliaLux-LED/HeliaLux-SmartControl/). It is *(heavily)* based on [pyHelialux](https://github.com/moretea/pyHelialux) by [moretea](https://github.com/moretea).

## Available sensors
* `tankname_blue`
* `tankname_green`
* `tankname_red`
* `tankname_white`
* `tankname_current_profile`

## How to install

Download this repo and copy it to your config/custom_components folder on your Home Assistant install.

Add the following to your Home Assistant config file.
```
sensor:
    - platform: juwel_helialux
      host: 1.2.3.4
      name: "Your Tank Name"
```
Change **host** to the ip address of your Juwel HeliaLux Smart Controller and change **name** to the name of your tank (Dave?).

Restart Home Assistant and your sensors should appear.
