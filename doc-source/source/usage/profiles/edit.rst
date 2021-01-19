**edit** - Edit a profile
=========================

**e4s-cl profile edit** [ NAME ] [ `OPTIONS` ]

OPTIONS := { **--new_name** | **--backend** | **--image** | **--source** | **--add-files** | **--remove-files** | **--add-libraries** | **--remove-libraries** }

Modify the profile associated to the name passed as an argument.
Passing a value to the options **--new_name**, **--backend**, **--image**, **--source** will overwrite the profile's corresponding field.
Passing a value to **--add-files**, **--remove-files**, **--add-libraries**, **--remove-libraries** will add or remove elements from the list of files or libraries, accordingly.

The name argument can be omitted in case a profile is selected, in which case the selected profile is modified.
