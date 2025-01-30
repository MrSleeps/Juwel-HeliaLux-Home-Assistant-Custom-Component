
# Juwel HeliaLux Smart Controller
**UPGRADE GUIDE**

This only applies if you are upgrading from the original basic/rubbish version (aka v0.0.6.2 and below) that I wrote a few years back, the one with the YAML config.

Because of my shockingly bad coding skills, the original version doesn't allow for an easy upgrade, sorry!

So it's a bit of a process to upgrade to the latest mildly singing and dancing version you see here.

**STEP ONE**

Remove the sensor entry from your Home Assistant config, head over to your favourite YAML editor and remove

```
sensor:
    - platform: juwel_helialux
      host: 1.2.3.4
      name: "Your Tank Name"
```

**STEP TWO**

Pop on over to Settings and Entities and manually delete the old sensors, I am aware this will probably break your automations/scripts.. Again, sorry!

**STEP THREE**
Restart Home Assistant.

**STEP FOUR**
Double check all your previous  tank sensors have been deleted.

**STEP FIVE**
Install the latest version of the custom component, either by HACS or old school manual way. [Find out how here!](https://github.com/MrSleeps/Juwel-HeliaLux-Home-Assistant-Custom-Component/blob/main/README.md)

**STEP SIX**
Fill out the details and hopefully marvel in the delight that is the new updated Juwel Helialux Custom Component.

For more info once you have done that, fly over to the [README](https://github.com/MrSleeps/Juwel-HeliaLux-Home-Assistant-Custom-Component/blob/main/README.md)