
# Juwel HeliaLux Smart Controller

This is a custom component for [Home Assistant](https://www.home-assistant.io/) that creates sensors to show details about your [Juwel HeliaLux Smart Controller](https://www.juwel-aquarium.co.uk/Products/Lighting/LED/HeliaLux-LED/HeliaLux-SmartControl/). It is *(heavily)* based on [pyHelialux](https://github.com/moretea/pyHelialux) by [moretea](https://github.com/moretea), but has been adapted to play nicer with Home Assistant (tested against 2025.1).

Once installed it gives you a bunch of sensors and a new light that you can turn on and off.

## Helialux firmware
**Your controller needs to have the latest v2.2.2 firmware from Juwel for this custom component to work**

## Available sensors

These sensors are read only, if you want to do things like turn the aquarium light on and off you will need to intereact with light.tankname.

* `tankname_blue` (Blue light intensity, 0-100)
* `tankname_green` (Green light intensity, 0-100)
* `tankname_red` (Red light intensity, 0-100)
* `tankname_white` (White light intensity, 0-100)
* `tankname_current_profile` (Currently selected profile)
* `tankname_profiles` (Count of available profiles)
* `tankname_manualcolorsimulationenabled` **This will be removed in a future version**
* `tankname_manualdaytimesimulationenabled` **This will be removed in a future version**
* `tankname_device_time` (Time on the controller)
* `tankname_tank_combined_sensor` (this combines all the above sensors into one)

## Other Entities/Devices
* `select.tankname_profiles` (Allows you to choose a profile that the controller will use)
* `binary_sensor.tankname_manual_color_simulation_enabled`
* `binary_sensor.tankname_manual_daytime_simulation_enabled`
* `light.tankname_light` (The main light, allows you to control your tank light)
* `Tank Device` (All sensors are linked to the relevant device)


## How to install

**Before we head down the install route, if you are upgrading from the original rubbish version I wrote years back, please read the [upgrade guide](https://github.com/MrSleeps/Juwel-HeliaLux-Home-Assistant-Custom-Component/blob/main/UPGRADE.md).**

Once you have done that...

You can either install it via Hacs (search for Juwel Helialux) or download this repo and copy it to your config/custom_components folder on your Home Assistant install.

Once you've done either of those, restart your Home Assistant. Once Home Assistant is back up, head over to Settings -> Integrations and add Juwel Helialux. Fill out the information (you'll need to know the host/ip). Your sensors and light should (hopefully) appear.

## Once installed

You'll have your sensors listed above and a new light (light.tankname_light) to play with.

## Things to be aware of

The Juwel Helialux unit is a bit clunky and is easily overloaded (mine at least). So when you are changing colours it can get overloaded and not do what you want it to do. 

**The controller website will cancel out all your changes if you visit the website manually! This includes embedding the page in Home Assistant (any time the controller website is opened it will take control of the controller and do its own thing).**

Also, Home Assistants way of dealing with colours on the colour wheel doesn't play overly well with the Juwel Helialux Controller. If you are having trouble getting just RGB colours then drag the white brightness down and have a wiggle with the colour wheel. I'm working to fix it but tbh, I don't really know what I am doing. Any other bugs then please post on GitHub.

## Bug Reports
Please follow the template when submitting a bug report, to help logs will be needed. To turn on debug logging for the integration you will need to add something like the following to your configuration.yml
```    logger:
      default: info`
      logs:
        custom_components.juwel_helialux: debug```

## Check your firmware version!
[jakerol](https://github.com/MrSleeps/Juwel-HeliaLux-Home-Assistant-Custom-Component/issues/4#issuecomment-1318268129) pointed out that v1 firmware don't appear to work with this custom component, please make sure your HeliaLux firmware is at least v2.1 (why wouldn't you be on v2.. v1 was ugly). You can update by heading over to your Juwel HeliaLux controller webpage, click on the settings click and click the info link at the bottom of the page (in the middle, possible an "i" icon) and then click firmware.
