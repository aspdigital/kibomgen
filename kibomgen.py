#
# Python script to generate a BOM with orderable part numbers from a KiCad netlist.
# Requires a CSV-formatted list of parts.
# created 2022-05-06 asp, derived from the standard KiCad script bom_csv_grouped_by_value.py
# Mod: 2022-05-10 asp, having the description in the result BOM is nice
#
### Requirements for the master parts list CSV file ####
# It must include the following columns with these exact names:
#
#   Part Number             Key into the database
#   Vendor                  The vendor name
#   Vendor P/N              The vendor's assigned part number
#   Package                 Footprint/package
#   Quantity On Hand        How many of these parts we have in stock (don't need to order)
#   Price Each (qty 25)     WAG cost for each part, based on last time we looked at Mouser
#
# the file may have other fields (comments, symbol name, etc) but they are ignored.
#
# RE: PART NUMBER.
# This is the GUID in the database for each part.
#
# It has the general form A-1000-0, where:
#   A     is a letter indicating general category (IC, connector, discrete, etc)
#   1000  is a number that is just a key and generally indicates "family" of parts
#   0     is a "variant" and generally has no meaning but ...
#
# the "family" is generally a convenience. It means "all parts with this value are highly similar
# and vary in only one parameter."
#
# For example, the LM317 regulator comes in several packages: TO-220, SOT-223, whatever.
# We can define A-1000 as the "family" of LM317 regulators, and the dash "variant" can indicate
# the package. We could, for example use 0 and 1 to indicate TO-220 and SOT-223. We could also
# just append the package TO-220 or SOT-223 as the variant, but I have chosen simplicity.
# In any case, the part number field in the symbol has to have the full number A-1000-0.
#
# Another example is connectors such as the common 0.1"-center box headers. They share the same base
# number say L-1000 for vertical-mount THT headers. The variant is the number of pins. The part
# number field in the symbol must always been complete: L-1000-10.
#
# The exception to the rule about "Full number in the PN field" is for certain parts where placing
# a symbol for a family part and then modifying the Value field greatly reduces the size of our library.
# This applies to resistors, capacitors, inductors and oscillators. For these devices, the PN field
# in the symbol only has the base family name, for example, B-1000 for 0805 1% resistors with no
# dash variant. Each instance of the symbol in a schematic must have the Value field changed to the
# actual part value. This script will then append the value to the base number and build a full
# part number, such as B-1000-10k0 for a 10k-ohm 0805 1% resistor.
#
# As part of the processing, then, each part in the schematic is then looked up in the parts database
# table by the PN.
#
# The output CSV file has the following columns:
#
# Part Number               
# count
# RefDesList
# Vendor P/N
# Value
# Vendor
# Package
# ext. cost
# Qty on hand



"""
    @package
    Output: CSV (comma-separated)
    Grouped By: Part number
    Sorted By: Part number
    Output Fields: Part Number, Count, Ref Des List, Vendor P/N, Value, Vendor, Package, ext. cost, quantity on hand 

    Command line: 
    python "pathToFile/kibomge.py" "%I" "%O.csv" "path_to_database.csv"
"""

from __future__ import print_function

# This requires two KiCad helper modules, which should be found in the scripting/plug-ins
# directory of a KiCad install.
import kicad_netlist_reader
import kicad_utils
import csv
import sys
import re
import pathlib

# for sorting by reference designator.
def natural_key(string_):
    return [int(s) if s.isdigit() else s for s in re.split(r'(\d+)', string_)]

# A helper function to convert a UTF8/Unicode/locale string read in netlist
# for python2 or python3
def fromNetlistText( aText ):
    if sys.platform.startswith('win32'):
        try:
            return aText.encode('utf-8').decode('cp1252')
        except UnicodeDecodeError:
            return aText
    else:
        return aText

# Generate an instance of a generic netlist, and load the netlist tree from
# the command line option. If the file doesn't exist, execution will stop
print("Reading netlist ", sys.argv[1])
net = kicad_netlist_reader.netlist(sys.argv[1])

# Open the master parts list and read the dictionary.
partsDBFile = sys.argv[3]
print("Reading parts list file :", partsDBFile)
partsListReader = csv.DictReader(open(partsDBFile))
# This gives us a list of dictionaries in the master parts list.
# the first row is the header. From Python docs:
#    The fieldnames parameter is a sequence.
#    If fieldnames is omitted, the values in the first row of file f will be used as the fieldnames.
# and it is expected that the file includes the fields names in the first row.
partsList = [row for row in partsListReader]

# get a list of all of the components in the netlist. each component has the standard fields.
# access standard fields directly with accessor methods.
# Use getField to get what's in a particular field. In our case we need the PN field.
print("Getting list of components in netlist")
components = net.getInterestingComponents()

# Go through each component and create a new "lookup" list of parts.
# This is a list of dictionaries. Each entry in the list has:
#   Part Number
#   Value
#   Count of this part
#   List of reference designators for this part number.
lookupList = []

# Now go through all of the components in the design.
#
# Some parts (capacitors, resistors, inductors, oscillators) have the base part type and number with the value
# added as the suffix. For those parts, the part number won't have a dash suffix. That suffix comes from the part
# value. So add it if necessary.
#
# Then combine all identical parts into one line item.
# For example, all part numbers B-1000-10k0 should be one one line in our BOM, with all reference designators
# listed. Each entry in our "lookup" list has what we need to build the final BOM: part number, count, reference
# designator list, value.

for c in components:   

    # first, fetch the part number for possible append.
    PartNum = c.getField("PN")
    # Fetch the reference designator, because we need only its first character, and this is cleaner
    # than c.getRef()[0]
    RefDes = c.getRef()
    print("RefDes : ", RefDes, "This component is ", PartNum)

    if RefDes[0] == 'C' or RefDes[0] == 'L' or RefDes[0] == 'R' or RefDes[0] == 'Y':
        PartNum = PartNum + '-' + c.getValue();
        print('\tNew part number is', PartNum)
        
    # Check the existing lookup list for the part. Test the part number.
    # If it doesn't exist, add it to the list, with a count of 1 and make sure
    # that the refdes list is initialized with the current refdes. If it does
    # exist, increment the count and add this refdes to the list.
    if not lookupList:
        # list is empty, just add this part to it.
        print('****Initializing lookupList')
        refdesList = [RefDes]
        thisEntry = {'PartNum': PartNum, 'value': c.getValue(), 'count': 1, 'RefDesList': refdesList}
        print(thisEntry)
        lookupList.append(thisEntry)
    else:
        # list is not empty. Go through it looking to see if our part number is already in it.
        gotIt = False
        for thisPart in lookupList:
            if thisPart['PartNum'] == PartNum:
                thisPart['count'] += 1
                thisPart['RefDesList'].append(RefDes)
                print('Part already in list. New entry: ', thisPart, ' Count = ', thisPart['count'])
                gotIt = True
                break
        print ('Got it: ', gotIt)
        if gotIt == False:
            refdesList = [RefDes]
            thisEntry = {'PartNum': PartNum, 'value': c.getValue(), 'count': 1, 'RefDesList': refdesList}
            lookupList.append(thisEntry)
            print('New part added to list: PartNum = ', PartNum, ' ....   Added ', thisEntry)

# Now we've got a list of all of the part numbers with the count of each as well as the relevant refdeses.
# Sort the reference designators for each part.
# Then match the company part number with the orderable part number.
print('\n\n******** Matching company part number with manufacturer number ******')
finalBomList = []
for thisPart in lookupList:
    print("thisPart: ", thisPart)
    # Sort reference designators.
    thisPart['RefDesList'].sort(key=natural_key)
    
    # Now match company part number with an orderable part number, if one is in our parts list.
    # If no match, vendor P/N flags as ???? so the user should check the BOM and then update
    # the parts list as necessary.
    for part in partsList:
        if part['Part Number'] == thisPart['PartNum']:
            #print 'Match!'
            print('Match! Vendor and part number: ', part['Vendor'], part['Vendor P/N'])
            # The parts database includes a price per part, pull that and multiply by the count so we can get a price guesstimate.
            # We add the running total cost to the end, because I don't know how to put it in the file at the end as a separate line.
            price = part['Price Each (qty 25)']
            cost = float(price.strip("$")) * float(thisPart['count'])
            print('Price: ', price, '  Extended cost: ', cost)
            # Add this part to the list of all parts/vendors/part numbers.
            finalBomList.append({'Part Number': thisPart['PartNum'], 'count': thisPart['count'], 'Vendor P/N': part['Vendor P/N'], 'Value': thisPart['value'], 'Vendor': part['Vendor'], 'Package': part['Package'], 'RefDesList': thisPart['RefDesList'], 'Description', part['Description'], 'ext. cost': cost, 'Qty on hand': part['Quantity On Hand']})
            break;
    else:
        # part was not found! This is an error.
        finalBomList.append({'Part Number': thisPart['PartNum'], 'count': thisPart['count'], 'Vendor P/N': '????', 'Value': thisPart['value'], 'Vendor': '????', 'Package': '????', 'RefDesList': thisPart['RefDesList'], 'Description': '????', 'ext. cost': 0, 'Qty on hand': '????'})

# Sort the Final BOM list by part type (A, B, C etc) and within the type by number and within number by value.
finalBomList.sort(key = lambda k: k['Part Number'])

# display the sorted BOM.
print("************* BOM *********")
for thatPart in finalBomList:
    print("Part: ", thatPart)
    
#
# write it to the result csv file.
#
finalBomFile = sys.argv[2]
fieldNames = ['Part Number', 'count', 'RefDesList', 'Vendor P/N', 'Value', 'Vendor',  'Package', 'Description', 'ext. cost', 'Qty on hand']
print('Writing BOM file ', finalBomFile)
with open(finalBomFile, 'w') as f:
    # first, write a header with some useful information.
    hwriter = csv.writer(f)
    print( "Source file:", net.getSource() )
    srcpath = pathlib.Path( net.getSource() )
    print("Source path: ", srcpath)
    src = srcpath.stem
    print("file name: ", src)
    header = ['Design file:', src, 'Date:', net.getDate()]
    hwriter.writerow(header)
    dwriter = csv.DictWriter(f, fieldnames=fieldNames, dialect='unix')
    dwriter.writeheader()
    dwriter.writerows(finalBomList)
f.close()
# Goodbye, World!
print ('DONE! BomFile ', sys.argv[2], 'written.')
