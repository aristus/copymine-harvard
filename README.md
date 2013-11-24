Harvard Library Bibliographic Dataset parser
===========

[carlos@bueno.org](mailto:carlos@bueno.org)

Harvard University publicly releases the 12+ million metadata records from
their library catalogs, including photos, journals, books, recordings and
manuscripts. Known as the [Harvard Library Bibliographic Dataset](http://openmetadata.lib.harvard.edu/bibdata),
documentation is available [here](http://openmetadata.lib.harvard.edu/sites/default/files/Harvard_Library_Bibliographic_Dataset_Documentation.pdf).

The dataset is in the public domain, but the data is in the arcane and wonky
"MARC21" format (see the Library of Congress' [official documentation](http://www.loc.gov/marc/bibliographic/)
on MARC21).

This is a parser for the data contained in the dump that can output in either
JSON or SQL. It makes use of Nathan Denny's MARC21 library, and adds a ton of
stuff on top, including friendly names for fields, and lots of heuristic
tricks to determine the content type of the items, which opens up even more
metadata encoded in the infamous "Record 008".

Usage
----------

````
   python marc.py sql|json [input] > your_output_file.json
````

Download and uncompress the Harvard dataset in the same directory (this script
expects the data to be in `data/hlom/`). Alternatively, you can specify an
individual source file as the `input` argument.

For example:

````
   python marc.py json > output.json
````

Also included are samples of the JSON and SQL output.

License
----------

Released under the "MIT" or "BSD" license scheme. See LICENSE file.

TODO
----------

* The SQL schema is terrible!
* More metadata parsing
* Better detection of music and audio
* Translate more fields
* alt_glyph support
