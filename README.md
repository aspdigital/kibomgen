# kibomgen, a BOM generator for KiCad v6
KiCad uses Python or XSL scripts to generate bills of materials from schematics. From within the KiCad Schematic Editor, the user simply chooses Tools => Generate BOM  from the main menu, or clicks the BOM icon from the top toolbar to open the Bill of Material (sic) dialog. KiCad ships with a few example scripts which can output a BOM in text, HTML or CSV format.
These scripts depend on information found in each symbol's properties. They give a list of parts, and can collate the same part and count them and provide a list of reference designators for them. 

There is one big problem with the example scripts. The standard KiCad libraries do not have any real ordeable part infomration. Out of the box, you can't do what most people need a BOM for: to provide a list of parts with valid part numbers that you can use for orders. Obviously, one way to manage this is to embed a manufacturer or distributor part number in each symbol, but this presents a lot of problems, not the least of which is how do you manage simple parts list resistors? Nobody wants a library full of a hundred different resistor symbols that vary only in part value. At some point, KiCad will have a way to manage libraries using a database, but that day is not yet here. I've come up with a fairly simply scheme which involves a simple database (a spreadsheet), one custom field in KiCad symbols, and a Python script to generate useful BOMs.

## What we need
A database of parts is used to keep track of every part we want to use in a design. Because I am not a database ninja, and honestly my parts list isn't giant, I decided to use a simple spreadsheet for my database. I use Macs, so I just use Apple's Numbers spreadsheet, which is rather competent. The only downside is that there's no way to programmatically access the contents of a Numbers spreadsheet from outside of Numbers, so after I make changes to my "database" I export the contents of the spreadsheet as a CSV file.

Each line in the spreadsheet is the information for exactly one part. It has expected information like vendor name, vendor part number, footprint and a description. It also tells me the name of the library it's in. There is a column for part cost which generally infomrational but not too useful. (The idea was to do a Mouser or Octopart lookup but I never got around to it.) You can see all of the fields in the Parts Database.numbers file.

In the first column of each line is the key: the part number. This part number is a "company" or "house" part number. Consider it to be a GUID.

The Numbers document's second sheet is a "key" which explains and defines my categories and numbering system.

All of the parts in my KiCad symbol libraries have a custom field called **PN**. The value in this field must match a part number defined in the Parts Database.

## Part Number format
The part number is a simple three-part text field with a general format of **A-1000-0**, where the three parts are defined as follows:

* **A** is a letter that generally indicates part type. A part type is an integrated circuit, a discrete semiconductor, a resistor, a capacitor, an oscillator, a connector, whatever. There is no relationship between this letter and a part's reference designator. It doesn't even have to be a letter. It's just a convenience.
* **1000** is a number indicating a specific part or part family (see below). The exact value of this part of the number is not important. All that matters is that they're unique.
* **0** is the indicator of a part variant. The meaning of this variant depends on the part itself. In the case of resistors, the variant is the value. In the case of ICs, you might want to have it indicate a different package, for example for a part that comes in PDIP and SOIC. If you like to have the PCB itself or the PCBA as a part, then it can indicate the revision. If the part doesn't need a variant, set it to 0.

### Non "family" parts

For these parts, the **PN** field in the symbol must be populated with the complete part number as defined in the database. The script matches on full part numbers, and will give an error if there is no match for a part placed on the schematic.

### Part "families"
One big problem faced by engineers setting up a parts library/BOM system is how to handle passives. Consider resistors. Nobody wants a resistor library filled with a hundred or more different resistor symbols, one for each value you use. If you want to change the resistor value, you need to pull a new part from the library. It gets ugly pretty quickly.

A solution is a part "family." Parts in a family vary in one and only one parameter. Again, resistors. Resistors come in different values, packages and tolerances. The most obvious thing to vary is the part value, so we can define a family as all 0805 1% resistors. Let's give these resistors a "base" part number: **B-1000**. We can use the part value as the variant, so a 10k 0805 1% resistor gets the part number **B-1000-10k0**. I have adopted the three-digit-plus-multiplier format for convenience and ease of parsing. A 100-ohm resistor is 100R; a 1 megohm resistor is 1M00.

SMT caps work in mostly the same manner: **C-1000-100pF** is a 100pF 5% C0G 0805 50V capacitor. **C-1000-1000pF** is a 1000pF 5% C0G 50V capacitor. **C-1001-100nF** is a 0.1uF 0805 X7R 50V capacitor. And so forth.

Inductors are similar, a base part number and a variant indicating the inductance value.

One more example: **J-1001-22.5792M** is a 7.0mm x 5.0mm 22.5792 MHz oscillator. **J-1008-25.000M** is a 25 MHz AVX crystal in a 3.2mm x 2.5mm package.

As of now, the only parts I've defined as families are resistors, capacitors, inductors and crystals, and the BOM processing script handles them correctly. The script looks for reference designator R, C, L and Y as special cases.

The **PN** field in the KiCad symbol for a family should have only the leading part type field (single letter) and the family number. The script will look for these types and concatenate the value to the base part number to get the full part number which will properly index into the database. 

## The BOM processing script
The script requires three command-line arguments.
* argv[1] is the input schematic, and this is automatically provided to the script as the %I argument by the generator.
* argv[2] is the output file in CSV format, and is automatically provided to the script as athe %O argument by the generator.
* argv[3] is the path to the CSV-format parts database.

Press the "Generate" button in the dialog to start the process. The window will show the progress of the script, and at the end the BOM CSV file will be in the same directory as the project.

## Final words
This script is based on the examples provided with KiCad, and has two of the provided files as dependencies: kicad_utils.py and kicad_netlist_reader.py. It is by no means an example of "great Python scripting," and surely can be improved. It works well enough for my use.
