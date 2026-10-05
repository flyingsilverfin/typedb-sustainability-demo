Notes on how I worked with the dataset.

## Part 1: the model

1) **reading the dataset a bit to understand what's going on**

- each row is a "trade flow"
- there are participants in the trade flow of commodities to do with import/export, countries, sources, mills, and refineries
- this dataset comes from the citation:
```
Benedict, J. J., Biddle, H., Gollnow, F., Heilmayr, R., Mueller, C., Ribeiro, V., & Suavet, C. (2024). Indonesia palm oil supply chain (2018–2022) (Version 1.2) [Data set]. Trase. https://doi.org/10.48650/X83N-7M36
```

2) **Because I'm impatient I'll first try to run go through the header and an example row and start writing things down**
```
#year	country_of_production	product_type	forest_500_palm_oil	zero_deforestation_indonesia_palm_oil	province_of_production	kabupaten_of_production	mill	mill_trase_id	mill_group	refinery
2022	INDONESIA	PALM OIL	3	NDPE COMMITMENT	KALIMANTAN TIMUR	BERAU	AGRO INDOMAS (BUMI JAYA)	ID-PALM-MILL-00011	GOODHOPE	NOT REFINED
```

Question: What would you start modeling? I start with the main entities, which are here the places [draw out places] in ER diagram.

I'm going to encode this into TypeQL directly.

[[SNIPPET 1]]
```
define

### Places ### 

attribute country_name, value string; 
attribute province_name, value string;
attribute kabupaten_name, value string;

entity country, 
  owns country_name @key;

entity province,
  owns province_name @key;

entity kabupaten, 
  owns kabupaten_name @key;
```

However, then it starts to look more complex!

3) **get stuck on the next group - columns aren't necessarily easy entities/attributes:**

```
# mill                          mill_group              refinery                 	
AGRI EASTBORNEO KENCANA	        KENCANA AGRI            NOT REFINED             
NIAGA MAS GEMILANG	            JC CHEMICAL             LDC EAST INDONESIA      
TAPIAN NADENGGAN (JAK LUAY)	    SINAR MAS	            SMART TBK (SURABAYA REFINERY)
DWIWIRA LESTARI JAYA            TRIPUTRA AGRO PERSADA	LDC EAST INDONESIA	

# refinery_group    exporter	                                exporter_group
NOT REFINED         SUMBER HIJAU UTAMA                          ROYAL GOLDEN EAGLE
LOUIS DREYFUS       LDC EAST INDONESIA	                        LOUIS DREYFUS
SINAR MAS           SINAR MAS AGRO RESOURCES AND TECHNOLOGY     SINAR MAS
LOUIS DREYFUS	    LDC EAST INDONESIA	                        LOUIS DREYFUS
```

The same names appear in multiple places, under different capacities?
It's not obvious whether a mill and a group should be different entities, or a refinery and a refinery group, export/exporter group, etc (importer side exists as well)

[ Draw out slide with this in ER ]

One model could be:
```
entity mill;
entity mill_group;
entity refinery;
entity refinery_group;
entity exporter;
entity exporter_group;
```

However, data summary says "XXX group groups XXX column into parent companies where applicable"

In addition, applying our understanding of what these different terms mean, it feels like 'mills' and 'refinderies' are maybe semantically closer together than to 'exporter'?

Question: what is an alternative representation that we might like to adopt here?

Answer: to me it feels like there are 'companies' and 'facilities' only, with some kind of ownership between them ("groups"). 'Exporter' is perhaps a role that can be fulfilled by companies?

[ Draw out slide with ER for the below, flattening the abstract behaviour ]

[[SNIPPET 2]]
```
define

### Companies and facilities ###

attribute facility_name, value string;
attribute company_name, value string;

entity facility @abstract,
  owns facility_name,
  plays ownership:owned @card(1);   # at most 1 owner
entity mill,
  sub facility;
entity refinery,
  sub facility;

entity company,
  owns company_name @key,
  plays ownership:owner;

relation ownership,
  relates owner @card(1),
  relates owned @card(1);
```

Interestingly, it seems like the Trase data is hiding or merging some information. We can see that in one row `LDC EAST INDONESIA` is named as both the refinery and the exporter. I'm going to assume that this means there's a company `LDC EAST INDONESIA`, which operates the exports and owns a refinery, which I'm just going to say shares the same name as the company.

```
# mill                          mill_group              refinery                 	
DWIWIRA LESTARI JAYA            TRIPUTRA AGRO PERSADA	LDC EAST INDONESIA	

# refinery_group    exporter	                                exporter_group
LOUIS DREYFUS	    LDC EAST INDONESIA	                        LOUIS DREYFUS
```

Note that in the same data row `LOUIS DREYFUS` is the 'parent' (group) of the refinery, so we will read this being a parent company of the `LDC EAST INDONESIA` company that owns the refinery.

How do we extend the TypeQL to allow companies to own other companies?
[[SNIPPET 3]]
```
define

entity company,
  plays ownership:owned;  ## ownership:owner preexists!
```

Once that is all committed, let's observe the schema so far in TypeDB Studio [ do a small tour with TypeDB Studio ].

4) Creating commodities

We have two types of commodities in this dataset: `PALM OIL` and `REFINED PALM OIL`. 

Question: how would you model this?

a) 1 entity type with an attribute
b) 2 independent entity types
c) 1 abstract, 2 sub-entity types

[ Discuss, benefits and tradeoffs ]

I go with a) as it's the simplest

[[ SNIPPET 4 ]]
```
define

### Commidities ### 
attribute commodity name,
  value string @values("palm oil", "refined palm oil");  # validated enum

entity commidity,
  owns commodity_name @key;
```

Challenge: work out how to implement the above 2-instances maximum with model c)

5) Creating trade flows

How would you model the trade flow itself? Note that in the data, not every trade flow moves a refined commodity so a `refinery` may not be participating!

[ discuss ]

[ Slide with ER diagram showing the trade flow as a relationship connecting all the different components, using our terms ]

```
define

### Trade flow ###

relation trade_flow,
  relates origin @card(1),
  relates mill @card(1),
  relates refiner @card(0..), # optional!
  relates exporter @card(1),
  relates importer @card(1),
  # relates port @card(1),  # skip - export simplification
  relates destination @card(1),
  relates commodity @card(1);

entity kabupaten, plays trade_flow:origin;
entity mill, plays trade_flow:mill;
entity refinery, plays trade_flow:refiner;
entity company, 
  plays trade_flow:importer,
  plays trade_flow:exporter;
entity country,
  plays trade_flow:destination;
```

This has created a single 6 or 7-way relationship in the graph, fully type checked and enforced by the database!


------

## Part 2: the data

I will provide a simplified dataset that follows the schema that I created above.