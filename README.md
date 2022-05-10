# kibomgen, a BOM generator for KiCad v6
KiCad uses Python or XSL scripts to generate bills of materials from schematics. From within the KiCad Schematic Editor, the user simply chooses Tools => Generate BOM  from the main menu, or clicks the BOM icon from the top toolbar to open the Bill of Material (sic) dialog. KiCad ships with a few example scripts which can output a BOM in text, HTML or CSV format.
These scripts depend on information found in each symbol's properties. They give a list of parts, and can collate the same part and count them and provide a list of reference designators for them. 

There is one big problem with the example scripts. The standard KiCad libraries do not have any real ordeable part information. Out of the box, you can't do what most people need a BOM for: to provide a list of parts with valid part numbers that you can use for orders. Obviously, one way to manage this is to embed a manufacturer or distributor part number in each symbol, but this presents a lot of problems, not the least of which is how do you manage simple parts like resistors? Nobody wants a library full of a hundred different resistor symbols that vary only in part value. At some point, KiCad will have a way to manage libraries using a database, but that day is not yet here. I've come up with a fairly simply scheme which involves a simple database (a spreadsheet), one custom field in KiCad symbols, and a Python script to generate useful BOMs.

## A database (or, in this case, a simple spreadsheet)
A database of parts is used to keep track of every part we want to use in a design. Because I am not a database ninja, and honestly my parts list isn't giant, I decided to use a simple spreadsheet for my database. I use Macs, so I just use Apple's Numbers spreadsheet, which is rather competent. The only downside is that there's no way to programmatically access the contents of a Numbers spreadsheet from outside of Numbers, so after I make changes to my "database" I export the contents of the spreadsheet as a CSV file.

The first line in the spreadsheet is the header. The Python CSV reader is clever enough to use the first line in the file for headers without any special intervention. 

There are several mandatory (for my script) fields in the parts database. They are, with exact spelling:
* **Part Number** the GUID for a part, in the format described below. This distinguishes parts from each other.
* **Vendor** the name of the part manufacturer or distributor of the part.
* **Vendor P/N** the exact orderable part number as provided by the manufacturer or distributor.
* **Package** the PCB footprint for the part, as embedded in the symbol's footprint field without the library name.
* **Description** describes the part for the human reading the BOM.
* **Quantity On Hand** indicates how many of this part we have in stock. It is helpful to know how many we have so we can determine how many to order.
* **Price Each (qty 25)** is a very rough indicator of parts cost based on whenever the last time you bothered to look it up. It is used to give a rough cost of the entire assembly.

My "database" has a number of other informational fields that are ignored by the BOM generation script, but they are useful for reference and design. These fields are: 
* **Symbol Name** The symbol name is what name is used for the part in the symbol library. In many cases, the symbol name matches the vendor part number (for example MMBT2222A). In other case it is desirable to have a "friendly" name for the symbol, so instead of SSL-LX3044YD we have LED_3mm_YELLOW. This is useful for resistor families, such as RES_0805_1%. This field is useful during schematic capture to help match the symbol to place on the sheet with what is in the library. If the part uses the Part Number for the symbol name, this field should be left blank.
* **Symbol Library** This field indicates the KiCad schematic library that stores the part. Obviously very helpful -- it tells you where to look when placing parts.
* **Footprint Library** This field indicates the footprint library that stores the footprint used by the part. Also helpful, especially since the footprint field does not include the library. 
* **Family** Synonomous with Symbol Name for part families, but a separate field to indicate that yes, this part is in a family.
* **Comments** Any extra information that might be useful
* **Alternate Vendor** if a part has a second source, this is the name of the vendor.
* **Alternate P/N** if a part has a second source, this is the vendor's assigned part number.

Therefore, each line in the spreadsheet is the information for exactly one part. The provided example Numbers document shows these fields.

In the first column of each line is the key: the part number. This part number is a "company" or "house" part number. Consider it to be a GUID. Regarding database maintenance, it's bad practice to re-use a part number one it is assigned.

The Numbers document's second sheet is a "key" which explains and defines my categories and numbering system. It is informational. When I generate a CSV file from the Numbers document, I delete the Key CSV file.

### Schematic symbols must have a **PN** field
All of the parts in my KiCad symbol libraries have a custom field called **PN**. The value in this field must match a part number defined in the Parts Database. I have the visibility flag of this field set to hide it in the schematic, just to avoid clutter.

### Part Number format
The part number is a simple three-part text field with a general format of **A-1000-0**, where the three parts are defined as follows:

* **A** is a letter that generally indicates part type. A part type is an integrated circuit, a discrete semiconductor, a resistor, a capacitor, an oscillator, a connector, whatever. There is no relationship between this letter and a part's reference designator. It doesn't even have to be a letter. It's just a convenience.
* **1000** is a number indicating a specific part or part family (see below). The exact value of this part of the number is not important. It doesn't have to be a number, and the "next" one doesn't have to be an increment over the current one. All that matters is that they're unique. 
* **0** is the indicator of a part variant. It doesn't have to be a number. The meaning of this variant depends on the part itself. In the case of resistors, the variant is the value (including SI unit multipliers). In the case of ICs, you might want to have it indicate a different package, for example for a part that comes in PDIP and SOIC. If you like to have the PCB itself or the PCBA as a part, then it can indicate the revision. If the part doesn't need a variant, set it to 0.

#### Non "family" parts

For these parts, the **PN** field in the symbol must be populated with the complete part number as defined in the database. The script matches on full part numbers, and will give an error if there is no match for a part placed on the schematic. 

The variant part of the part number can be used for whatever you might find interesting. One example: I use 0.1"-center box headers in various sizes, from 10 pins (2 rows of 5 pins each) to 20 pins (2 rows of 10 pins each). Part **L-1000-10** is the 2x5 header; part **L-1000-20** is the 2x10 header.

#### Part "families"
One big problem faced by engineers setting up a parts library/BOM system is how to handle passives. Consider resistors. Nobody wants a resistor library filled with a hundred or more different resistor symbols, one for each value you use. If you want to change the resistor value, you need to pull a new part from the library. It gets ugly pretty quickly.

A possible solution is a part "family." Parts in a family vary in one and only one parameter. Again, resistors. Resistors come in different values, packages and tolerances. The most obvious thing to vary is the part value, so we can define a family as all 0805 1% resistors. Let's give these resistors a "base" part number: **B-1000**. We can use the part value as the variant, so a 10kΩ 0805 1% resistor gets the part number **B-1000-10k0**. I have adopted the three-digit-plus-multiplier format for convenience and ease of parsing. A 100Ω resistor is 100R; a 1 megohm resistor is 1M00.

I have potentiometers as type K in my database, so for example **K-1005-10k** is a Bourns PTD902-2020K-A103 pot. The symbol for this pot has only **K-1005** in its **PN** field and the script correctly contatenates it with the Value field to get the database part number.

SMT caps work in mostly the same manner: **C-1000-100pF** is a 100pF 5% C0G 0805 50V capacitor. **C-1000-1000pF** is a 1000pF 5% C0G 50V capacitor. **C-1001-100nF** is a 0.1μF 0805 X7R 50V capacitor. And so forth.

Inductors are similar, a base part number and a variant indicating the inductance value.

One more example: **J-1001-22.5792M** is a 7.0mm x 5.0mm 22.5792 MHz oscillator. **J-1008-25.000M** is a 25 MHz AVX crystal in a 3.2mm x 2.5mm package.

The key to remember is that the script is a bit stupid. It wants to match the variant exactly, so the value 10k0 is not the same as 10K0 and certainly not the same as 10K. You have to make sure the Value in your design matches the variant field in the database part number. To be fair, though, the SI prefix for kilo is lower-case`k` and the prefix for mega is upper-case`M` so get it right! If you specify a 25 mHz oscillator your design might not work as you expect.

As of now, the only parts I've defined as families are resistors, capacitors, inductors and crystals/oscillators, and the BOM processing script handles them correctly. The script looks for reference designator R, C, L and Y as special cases. Obviously this can be expanded as desired.

Finally, the **PN** field in the KiCad symbol for a family should have only the leading part type field (single letter) and the family number. The script will look for these types and concatenate the value to the base part number to get the full part number which will properly index into the database. 

## The BOM processing script

### Dependencies and installation
The script depends on two scripts that should be included in the KiCad installer: `kicad_netlist_reader.py` and `kicad_utils.py`. They are generally found in the `scripting/plugins` directory, along with the standard KiCad BOM-generating scripts and the footprint wizards. You should put `kibomgen.py` in that directory, too, although note that if you update your KiCad installation and you put the script in a standard location, it might be deleted.

Tell KiCad Schematic that the script exists by clicking the + icon below the list of BOM generator scripts in the Bill of Material dialog. Mouse around in the Finder/whatever until you locate the script. As far as I can tell, KiCad Schematic does not scan the plug-in directory for scripts, so you have to add it manually.

Note that KiCad wants full paths for everything, so the command line is pretty ugly. The good news is that KiCad will set the path to Python and the path to the script correctly. You will need to add the path to the CSV file for the database. When you set this up, everything is saved as a preference and will work across projects. 

### Usage
The script requires three command-line arguments (in addition to argv[0] which of course is the script itself).

* argv[1] is the input schematic, and this is automatically provided to the script as the %I argument by the generator.
* argv[2] is the output file in CSV format, and is automatically provided to the script as athe %O argument by the generator.
* argv[3] is the path to the CSV-format parts database.

As noted above, when you add the script to the list of BOM generators, Schematic will automatically give the correct set-up for the first two arguments, and you will have to provide the path to the database CSV file.

Press the "Generate" button in the dialog to start the process. The window will show the progress of the script, and at the end the BOM CSV file will be in the same directory as the project.

<img width="1607" alt="kibomgen" src="https://user-images.githubusercontent.com/6307155/167672725-457332aa-aa0d-4411-b4c7-c29e0b8bc413.png">

## Final words
This script is based on the examples provided with KiCad, and has two of the provided files as dependencies: `kicad_utils.py` and `kicad_netlist_reader.py`. It is by no means an example of "great Python scripting," and surely can be improved. It works well enough for my use.

I use Numbers because it is included with all Macs and works well enough. If you prefer Excel, OpenOffice or Google Sheets, you can use them to create your own spreadsheet. In all cases, you must provide the header with the mandatory fields described above. (Or you could modify the script.)

As for "why not use [Bomist](https://bomist.com) or [partkeepr](https://partkeepr.org) or [PartsBox](https://partsbox.com) for the database? A good question. A lazy answer is that I started out with the spreadsheet, and my needs haven't gotten to the point where I need a full database for parts inventory. And that's really what the databases are for -- to manage inventory. 

### Things to do:
1. Add hook to an AppleScript that exports the CSV from a Numbers document prior to starting the rest of the process. This will eliminate the need to manually do so, minimizing errors. 
2. Accept a "number of kits to assemble" parameter, so the script can tell us how many parts we need to order over and above what we have in stock so we can create assembly kits.
3. Support for part variants, including do-not-stuff directives.
4. Actually use Alternate Vendor and Alternate P/N
5. After determining the vendor name and part number and the quantity of parts used in the design, look up the part cost at Mouser or wherever instead of relying on the Qty field in the database, for a more up-to-date price estimate. This might be more accurate if the number of kits to prepare is available.
