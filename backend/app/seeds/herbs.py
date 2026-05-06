"""
Seed — 20 common Nigerian medicinal herbs with compounds.

Run standalone:
    cd backend
    python -m app.seeds.herbs

Or call seed_herbs(db) from application code.
"""
import os
import sys

# ---------------------------------------------------------------------------
# Seed data
# ---------------------------------------------------------------------------

HERBS_DATA = [
    {
        "name_english": "Bitter Leaf",
        "scientific_name": "Vernonia amygdalina",
        "name_igbo": "Onugbu",
        "name_yoruba": "Ewuro",
        "name_hausa": "Shiwaka",
        "description": (
            "A perennial shrub native to tropical Africa. Widely used in soups (ofe onugbu) and "
            "traditional medicine. Extracts demonstrate antimalarial, antidiabetic, hepatoprotective "
            "and anti-inflammatory activity in multiple in-vitro and in-vivo studies."
        ),
        "region_found": "Pan-Nigeria; most abundant in southern and eastern states",
        "compounds": [
            {
                "compound_name": "Vernodalin",
                "chemical_formula": "C22H24O7",
                "medicinal_use": "Antiparasitic sesquiterpene lactone; inhibits Plasmodium falciparum and Trypanosoma species",
                "source_study": "Jisaka et al. (1993), Phytochemistry 34(2):409-413",
            },
            {
                "compound_name": "Vernolide",
                "chemical_formula": "C20H24O7",
                "medicinal_use": "Antimalarial and antitumour sesquiterpene lactone; induces apoptosis in cancer cell lines",
                "source_study": "Iwalokun et al. (2006), African Journal of Biotechnology",
            },
            {
                "compound_name": "Luteolin",
                "chemical_formula": "C15H10O6",
                "medicinal_use": "Anti-inflammatory flavonoid; antioxidant; antidiabetic via NF-kB inhibition",
                "source_study": "Erasto et al. (2007), Journal of Ethnopharmacology 113(1):148-154",
            },
            {
                "compound_name": "Chlorogenic acid",
                "chemical_formula": "C16H18O9",
                "medicinal_use": "Reduces postprandial blood glucose; antioxidant; hepatoprotective",
                "source_study": "Clifford (2000), Journal of the Science of Food and Agriculture 80(7):1033-1043",
            },
        ],
    },
    {
        "name_english": "Moringa",
        "scientific_name": "Moringa oleifera",
        "name_igbo": "Okwe oyibo",
        "name_yoruba": "Ewe ile",
        "name_hausa": "Zogale",
        "description": (
            "The 'miracle tree' — leaves, seeds, pods and bark are all medicinal. One of the most "
            "nutrient-dense plants known. Clinically studied for malnutrition, diabetes and hypertension."
        ),
        "region_found": "Pan-Nigeria; widely cultivated nationwide",
        "compounds": [
            {
                "compound_name": "Isothiocyanates (Moringin)",
                "chemical_formula": "C14H19NOS2",
                "medicinal_use": "Antimicrobial, anti-inflammatory; inhibits cancer cell proliferation in vitro",
                "source_study": "Fahey (2005), Trees for Life Journal 1(5)",
            },
            {
                "compound_name": "Quercetin",
                "chemical_formula": "C15H10O7",
                "medicinal_use": "Antioxidant; reduces blood pressure; anti-inflammatory; antiviral flavonoid",
                "source_study": "Kasolo et al. (2010), Journal of Medicinal Plants Research",
            },
            {
                "compound_name": "Kaempferol",
                "chemical_formula": "C15H10O6",
                "medicinal_use": "Antidiabetic; improves insulin sensitivity; cardioprotective flavonoid",
                "source_study": "Anwar et al. (2007), Phytotherapy Research 21(1):17-25",
            },
            {
                "compound_name": "Niazimicin",
                "chemical_formula": None,
                "medicinal_use": "Thiocarbamate glycoside shown to inhibit tumour-promoter activity",
                "source_study": "Faizi et al. (1994), Journal of Natural Products 57(9):1256-1261",
            },
        ],
    },
    {
        "name_english": "Neem (Dogoyaro)",
        "scientific_name": "Azadirachta indica",
        "name_igbo": "Ogwu akom",
        "name_yoruba": "Igi dongoyaro",
        "name_hausa": "Dagon-yaro",
        "description": (
            "Evergreen tree with powerful insecticidal, antimicrobial and antimalarial properties. "
            "Every part — bark, leaves, seeds, oil — is used medicinally. Azadirachtin is one of "
            "the most effective natural insecticides known."
        ),
        "region_found": "Pan-Nigeria; originally introduced, now fully naturalised",
        "compounds": [
            {
                "compound_name": "Azadirachtin",
                "chemical_formula": "C35H44O16",
                "medicinal_use": "Potent insecticide and antiparasitic; disrupts moulting hormones in insects and parasites",
                "source_study": "Schmutterer (1990), Annual Review of Entomology 35:271-297",
            },
            {
                "compound_name": "Nimbin",
                "chemical_formula": "C30H36O9",
                "medicinal_use": "Anti-inflammatory, antipyretic and antifungal triterpenoid",
                "source_study": "Biswas et al. (2002), Current Science 82(11):1336-1345",
            },
            {
                "compound_name": "Nimbidin",
                "chemical_formula": "C28H34O7",
                "medicinal_use": "Antibacterial and anti-ulcer; inhibits Helicobacter pylori growth",
                "source_study": "Akah & Okafor (1992), African Journal of Traditional Medicine",
            },
            {
                "compound_name": "Gedunin",
                "chemical_formula": "C28H34O7",
                "medicinal_use": "Antimalarial limonoid; disrupts protein folding in Plasmodium falciparum HSP90",
                "source_study": "Kanokmedhakul et al. (2005), Journal of Natural Products",
            },
        ],
    },
    {
        "name_english": "African Basil (Scent Leaf)",
        "scientific_name": "Ocimum gratissimum",
        "name_igbo": "Nchuanwu",
        "name_yoruba": "Efirin",
        "name_hausa": "Daidoya",
        "description": (
            "Highly aromatic shrub with strong antimicrobial, antifungal and insect-repellent properties. "
            "Essential oil is key in traditional remedies for diarrhoea, respiratory infections "
            "and fungal skin conditions. Widely used as a culinary herb."
        ),
        "region_found": "Pan-Nigeria; thrives in humid southern and middle-belt regions",
        "compounds": [
            {
                "compound_name": "Eugenol",
                "chemical_formula": "C10H12O2",
                "medicinal_use": "Analgesic and local anaesthetic; antibacterial against E. coli and S. aureus; antifungal",
                "source_study": "Nakamura et al. (1998), Phytotherapy Research 12(1):59-61",
            },
            {
                "compound_name": "Thymol",
                "chemical_formula": "C10H14O",
                "medicinal_use": "Potent antifungal and antibacterial; active against Candida and dermatophytes",
                "source_study": "Orafidiya et al. (2004), International Journal of Aromatherapy",
            },
            {
                "compound_name": "Linalool",
                "chemical_formula": "C10H18O",
                "medicinal_use": "Anxiolytic, sedative and anti-inflammatory monoterpene alcohol",
                "source_study": "Kamatou & Viljoen (2008), Journal of American Oil Chemists Society",
            },
        ],
    },
    {
        "name_english": "Soursop (Graviola)",
        "scientific_name": "Annona muricata",
        "name_igbo": "Obubo",
        "name_yoruba": "Esinsin",
        "name_hausa": "Tuwon biri",
        "description": (
            "Tropical tree whose leaves, fruit and seeds have significant anticancer, antimicrobial and "
            "antiparasitic properties. Acetogenins found in soursop leaves are among the most potent "
            "naturally occurring cytotoxic compounds. Widely consumed as a fruit across southern Nigeria."
        ),
        "region_found": "Southern Nigeria; Ogun, Ondo, Cross River, Rivers states",
        "compounds": [
            {
                "compound_name": "Annonacin",
                "chemical_formula": "C35H64O4",
                "medicinal_use": "Cytotoxic acetogenin; selectively toxic to MCF-7 breast and HeLa cervical cancer lines",
                "source_study": "Oberlies et al. (1997), Cancer Letters 115(1):73-79",
            },
            {
                "compound_name": "Annomuricin E",
                "chemical_formula": "C35H62O5",
                "medicinal_use": "Inhibits cancer cell ATP production by blocking mitochondrial Complex I",
                "source_study": "Moghadamtousi et al. (2015), Scientific Reports 5:12770",
            },
            {
                "compound_name": "Muricapentocin",
                "chemical_formula": "C35H64O5",
                "medicinal_use": "Antiparasitic; active against Leishmania and Trypanosoma species",
                "source_study": "Zeng et al. (1996), Journal of Natural Products 59(11):1035-1042",
            },
        ],
    },
    {
        "name_english": "Pawpaw Leaf (Papaya)",
        "scientific_name": "Carica papaya",
        "name_igbo": "Okwuru-ojo",
        "name_yoruba": "Ibepe",
        "name_hausa": "Gwanda",
        "description": (
            "Carica papaya leaf extract is clinically validated for increasing platelet count in dengue fever. "
            "The latex contains papain, a proteolytic enzyme used in wound debridement. "
            "In Nigerian ethnomedicine, leaf tea is used for malaria, liver disorders and as an anthelmintic."
        ),
        "region_found": "Pan-Nigeria; cultivated nationwide",
        "compounds": [
            {
                "compound_name": "Papain",
                "chemical_formula": None,
                "medicinal_use": "Proteolytic enzyme; wound debridement; digestive enzyme supplement; meat tenderisation",
                "source_study": "Bhutani et al. (2010), International Journal of Pharmaceutics",
            },
            {
                "compound_name": "Carpaine",
                "chemical_formula": "C28H50N2O4",
                "medicinal_use": "Alkaloid with anthelmintic, antiamoebic and mild cardiovascular depressant activity",
                "source_study": "Burdick (1971), Economic Botany 25(4):363-365",
            },
            {
                "compound_name": "Quercetin",
                "chemical_formula": "C15H10O7",
                "medicinal_use": "Promotes thrombopoiesis — mechanism behind platelet-boosting effect in dengue fever",
                "source_study": "Subenthiran et al. (2013), Evidence-Based Complementary and Alternative Medicine",
            },
        ],
    },
    {
        "name_english": "Aloe Vera",
        "scientific_name": "Aloe barbadensis miller",
        "name_igbo": "Akata oji",
        "name_yoruba": "Ahon ekun",
        "name_hausa": "Zabibi",
        "description": (
            "Succulent plant used topically and internally. Gel is widely used for wound healing, burns "
            "and skin conditions. The latex (aloin) acts as a stimulant laxative. "
            "In Nigeria, fresh gel is applied to skin infections, burns and used as a hair treatment."
        ),
        "region_found": "Pan-Nigeria; widely cultivated; thrives in semi-arid north",
        "compounds": [
            {
                "compound_name": "Acemannan",
                "chemical_formula": None,
                "medicinal_use": "Immunomodulatory polysaccharide; accelerates wound healing by stimulating macrophage activity",
                "source_study": "Pugh et al. (2001), International Immunopharmacology 1(7):1275-1284",
            },
            {
                "compound_name": "Aloin (Barbaloin)",
                "chemical_formula": "C21H22O9",
                "medicinal_use": "Stimulant laxative anthraquinone glycoside; antifungal and UV-protective",
                "source_study": "Yagi et al. (2002), Journal of Gastroenterology 37(Suppl 14):9-10",
            },
            {
                "compound_name": "Aloe-Emodin",
                "chemical_formula": "C15H10O5",
                "medicinal_use": "Anthraquinone; antimicrobial, antiviral and anti-inflammatory; studied for anticancer activity",
                "source_study": "Chen et al. (2007), Food and Chemical Toxicology 45(10):1897-1902",
            },
        ],
    },
    {
        "name_english": "Turmeric",
        "scientific_name": "Curcuma longa",
        "name_igbo": "Ohu-beke",
        "name_yoruba": "Atale pupa",
        "name_hausa": "Gangamau",
        "description": (
            "Rhizomatous plant in the ginger family. Curcumin is one of the most studied natural compounds "
            "globally, with documented anti-inflammatory, antioxidant, anticancer and neuroprotective properties. "
            "Used in Nigerian traditional medicine for joint pain, wound healing and liver disorders."
        ),
        "region_found": "Southwestern and southeastern Nigeria; Edo, Ondo, Ogun states",
        "compounds": [
            {
                "compound_name": "Curcumin",
                "chemical_formula": "C21H20O6",
                "medicinal_use": "Anti-inflammatory; inhibits NF-kB and COX-2; studied in Alzheimer's disease and cancer",
                "source_study": "Aggarwal et al. (2007), Annals of the New York Academy of Sciences 1114:1-14",
            },
            {
                "compound_name": "Bisdemethoxycurcumin",
                "chemical_formula": "C19H16O4",
                "medicinal_use": "Curcuminoid with anticancer and anti-inflammatory properties; potentiates curcumin",
                "source_study": "Sandur et al. (2007), Carcinogenesis 28(8):1765-1773",
            },
            {
                "compound_name": "Ar-Turmerone",
                "chemical_formula": "C15H20O",
                "medicinal_use": "Antimicrobial, antiparasitic and neuroregenerative sesquiterpene ketone",
                "source_study": "Lim et al. (2014), Stem Cell Research & Therapy 5(1):121",
            },
        ],
    },
    {
        "name_english": "Ginger",
        "scientific_name": "Zingiber officinale",
        "name_igbo": "Jinja",
        "name_yoruba": "Atale",
        "name_hausa": "Citta",
        "description": (
            "Tropical rhizome with one of the longest histories of medicinal use. "
            "In Nigeria, fresh ginger treats nausea, respiratory infections, menstrual pain and digestive disorders. "
            "Gingerols convert to more potent shogaols upon drying."
        ),
        "region_found": "Pan-Nigeria; major production in Kaduna, Nasarawa and Gombe states",
        "compounds": [
            {
                "compound_name": "[6]-Gingerol",
                "chemical_formula": "C17H26O4",
                "medicinal_use": "Anti-nausea; anti-inflammatory via prostaglandin and leukotriene inhibition; antiemetic in chemotherapy",
                "source_study": "Ernst & Pittler (2000), British Journal of Anaesthesia 84(3):367-371",
            },
            {
                "compound_name": "[6]-Shogaol",
                "chemical_formula": "C17H24O3",
                "medicinal_use": "More potent than gingerol; neuroprotective; anticancer; inhibits 5-HT3 receptors",
                "source_study": "Zick et al. (2008), Cancer Epidemiology Biomarkers Prevention",
            },
            {
                "compound_name": "Zingerone",
                "chemical_formula": "C11H14O3",
                "medicinal_use": "Antidiarrheal; antioxidant; reduces gut motility; protective against E. coli enterotoxins",
                "source_study": "Huang et al. (1991), Journal of Agriculture and Food Chemistry 39(10):1698-1704",
            },
        ],
    },
    {
        "name_english": "Garlic",
        "scientific_name": "Allium sativum",
        "name_igbo": "Ayu",
        "name_yoruba": "Ayuu",
        "name_hausa": "Tafarnuwa",
        "description": (
            "One of the oldest and most thoroughly studied medicinal plants. Cardiovascular benefits, "
            "antimicrobial properties and immune-boosting effects are backed by hundreds of clinical trials. "
            "In Nigerian traditional medicine, raw garlic treats hypertension, infections and serves as a tonic."
        ),
        "region_found": "Pan-Nigeria; commercial cultivation in northern states (Plateau, Kaduna)",
        "compounds": [
            {
                "compound_name": "Allicin",
                "chemical_formula": "C6H10OS2",
                "medicinal_use": "Broad-spectrum antimicrobial; antifungal; reduces LDL cholesterol and blood pressure",
                "source_study": "Ried et al. (2016), Journal of Nutrition 146(2):389S-396S",
            },
            {
                "compound_name": "Ajoene",
                "chemical_formula": "C9H14OS3",
                "medicinal_use": "Anticoagulant; antimicrobial; anticancer; inhibits platelet aggregation and cancer cell cycle",
                "source_study": "Nabekura et al. (2010), Anticancer Research 30(9):3425-3430",
            },
            {
                "compound_name": "S-Allylcysteine (SAC)",
                "chemical_formula": "C6H11NO2S",
                "medicinal_use": "Water-soluble antioxidant; neuroprotective; reduces diabetic complications",
                "source_study": "Guo et al. (2015), Phytomedicine 22(1):1-6",
            },
        ],
    },
    {
        "name_english": "Lemongrass",
        "scientific_name": "Cymbopogon citratus",
        "name_igbo": "Achara ehi",
        "name_yoruba": "Koriko oba",
        "name_hausa": "Tsaura",
        "description": (
            "Tropical grass with strong lemon fragrance. Essential oil has potent antibacterial, "
            "antifungal and insect-repellent properties. Lemongrass tea is used traditionally to lower "
            "fever, reduce anxiety and treat digestive problems. A top ingredient in Nigerian herbal teas."
        ),
        "region_found": "Pan-Nigeria; thrives in humid southern regions",
        "compounds": [
            {
                "compound_name": "Citral (Geranial + Neral)",
                "chemical_formula": "C10H16O",
                "medicinal_use": "Primary monoterpene aldehyde; antimicrobial, antifungal and anxiolytic; lemon scent source",
                "source_study": "Olorunnisola et al. (2011), African Journal of Biotechnology 10(14):2682-2687",
            },
            {
                "compound_name": "Geraniol",
                "chemical_formula": "C10H18O",
                "medicinal_use": "Antioxidant; anti-inflammatory; anticancer monoterpene; repels mosquitoes and ticks",
                "source_study": "Prashar et al. (2004), International Journal of Aromatherapy",
            },
            {
                "compound_name": "Myrcene",
                "chemical_formula": "C10H16",
                "medicinal_use": "Analgesic and sedative terpene; potentiates the effect of other active compounds",
                "source_study": "Rao et al. (1990), Planta Medica 56(2):107-110",
            },
        ],
    },
    {
        "name_english": "Hibiscus (Zobo)",
        "scientific_name": "Hibiscus sabdariffa",
        "name_igbo": "Isu",
        "name_yoruba": "Iso / Isapa",
        "name_hausa": "Yakwa / Zoborodo",
        "description": (
            "Dried calyces are the source of zobo — Nigeria's most popular herbal beverage. "
            "Clinically demonstrated antihypertensive, hepatoprotective and lipid-lowering effects. "
            "Multiple RCTs confirm blood pressure reduction comparable to 25mg hydrochlorothiazide."
        ),
        "region_found": "Northern Nigeria; Kano, Jigawa, Zamfara, Sokoto states",
        "compounds": [
            {
                "compound_name": "Delphinidin-3-sambubioside",
                "chemical_formula": "C26H29O15+",
                "medicinal_use": "Major anthocyanin; antihypertensive via ACE inhibitory activity",
                "source_study": "Ojeda et al. (2010), Journal of Ethnopharmacology 130(2):386-393",
            },
            {
                "compound_name": "Hibiscus acid (Hydroxycitric acid)",
                "chemical_formula": "C6H8O8",
                "medicinal_use": "Inhibits lipogenesis; promotes weight management; anti-nephrolithiasis",
                "source_study": "Adigun et al. (2006), West African Journal of Medicine 25(1):1-5",
            },
            {
                "compound_name": "Quercetin",
                "chemical_formula": "C15H10O7",
                "medicinal_use": "Antioxidant; hepatoprotective; cardioprotective flavonoid",
                "source_study": "Gurrola-Diaz et al. (2010), Phytomedicine 17(7):500-505",
            },
        ],
    },
    {
        "name_english": "African Walnut",
        "scientific_name": "Tetracarpidium conophorum",
        "name_igbo": "Ukpa / Asala",
        "name_yoruba": "Asala",
        "name_hausa": None,
        "description": (
            "Climbing shrub producing hard-shelled nuts consumed across southern Nigeria. "
            "Rich in omega-3 fatty acids, polyphenols and minerals. Traditional uses include "
            "fertility enhancement, anti-inflammatory treatment and management of hypertension."
        ),
        "region_found": "Southern Nigeria; Anambra, Enugu, Oyo, Osun states",
        "compounds": [
            {
                "compound_name": "Ellagic acid",
                "chemical_formula": "C14H6O8",
                "medicinal_use": "Antioxidant polyphenol; antiproliferative against cancer cells; prevents DNA oxidative damage",
                "source_study": "Taiwo et al. (2012), African Journal of Biochemistry Research 6(3):51-57",
            },
            {
                "compound_name": "Juglone",
                "chemical_formula": "C10H6O3",
                "medicinal_use": "Antimicrobial, antifungal and cytotoxic naphthoquinone; inhibits bacteria and Candida",
                "source_study": "Alisi et al. (2008), African Journal of Biotechnology 7(24):4525-4529",
            },
            {
                "compound_name": "Alpha-Linolenic acid",
                "chemical_formula": "C18H30O2",
                "medicinal_use": "Essential omega-3; cardioprotective; anti-inflammatory precursor to EPA and DHA",
                "source_study": "Nwosu (2012), Journal of Food Composition and Analysis 26(1-2):152-158",
            },
        ],
    },
    {
        "name_english": "African Star Apple (Agbalumo)",
        "scientific_name": "Chrysophyllum albidum",
        "name_igbo": "Udara",
        "name_yoruba": "Agbalumo",
        "name_hausa": "Agwaluma",
        "description": (
            "Large forest tree with sweet-sour fruits. The fruit, bark and leaves are used medicinally. "
            "Rich in vitamin C; used for gum disease, toothache and sore throat. Bark used for "
            "yellow fever, skin diseases and diarrhoea."
        ),
        "region_found": "Southern and western Nigeria; Lagos, Ogun, Osun, Rivers, Anambra states",
        "compounds": [
            {
                "compound_name": "Ascorbic acid (Vitamin C)",
                "chemical_formula": "C6H8O6",
                "medicinal_use": "High concentration (>25mg/100g); antioxidant; immune stimulant; promotes wound healing",
                "source_study": "Ihekoronye & Ngoddy (1985), Integrated Food Science and Technology for the Tropics",
            },
            {
                "compound_name": "Quercetin",
                "chemical_formula": "C15H10O7",
                "medicinal_use": "Antidiabetic via alpha-glucosidase and alpha-amylase inhibition; anti-inflammatory",
                "source_study": "Akinmoladun et al. (2010), African Journal of Biotechnology",
            },
            {
                "compound_name": "Ellagic acid",
                "chemical_formula": "C14H6O8",
                "medicinal_use": "Antibacterial against oral pathogens; explains traditional use for toothache and gum disease",
                "source_study": "Farombi & Owoeye (2011), International Journal of Environmental Research and Public Health",
            },
        ],
    },
    {
        "name_english": "Uziza Leaf",
        "scientific_name": "Piper guineense",
        "name_igbo": "Uziza",
        "name_yoruba": "Iyere",
        "name_hausa": "Masoro",
        "description": (
            "Climbing pepper plant indispensable in Igbo cuisine and traditional medicine. "
            "Used postpartum to aid recovery, in pepper soup for respiratory infections and as anthelmintic. "
            "Volatile oils have significant antimicrobial and antifungal activity."
        ),
        "region_found": "Southern Nigeria; predominantly southeastern Igbo-speaking states",
        "compounds": [
            {
                "compound_name": "Piperine",
                "chemical_formula": "C17H19NO3",
                "medicinal_use": "Bioavailability enhancer for other drugs; anti-inflammatory; analgesic; inhibits P-gp efflux pump",
                "source_study": "Meghwal & Goswami (2013), Nutrition and Metabolic Insights 6:67-76",
            },
            {
                "compound_name": "Caryophyllene",
                "chemical_formula": "C15H24",
                "medicinal_use": "Anti-inflammatory via CB2 receptor agonism; analgesic; antifungal sesquiterpene",
                "source_study": "Gertsch et al. (2008), PNAS 105(26):9099-9104",
            },
            {
                "compound_name": "Safrole",
                "chemical_formula": "C10H10O2",
                "medicinal_use": "Antimicrobial and antifungal; CAUTION: hepatotoxic at high doses — regulated substance",
                "source_study": "Edenharder et al. (1993), Mutation Research 287(2):261-278",
            },
        ],
    },
    {
        "name_english": "Utazi",
        "scientific_name": "Gongronema latifolium",
        "name_igbo": "Utazi",
        "name_yoruba": "Arokeke",
        "name_hausa": None,
        "description": (
            "Climbing shrub with bitter leaves used in southeastern Nigeria for culinary and medicinal purposes. "
            "Added to pepper soup and nkwobi. Traditionally used to manage diabetes, lower blood sugar "
            "after meals and detoxify the liver. Pharmacological studies confirm hypoglycaemic activity."
        ),
        "region_found": "Southeastern Nigeria; Anambra, Enugu, Imo, Cross River states",
        "compounds": [
            {
                "compound_name": "Luteolin",
                "chemical_formula": "C15H10O6",
                "medicinal_use": "Alpha-glucosidase inhibitor; antidiabetic; anti-inflammatory via COX-2 inhibition",
                "source_study": "Morebise et al. (2002), Phytotherapy Research 16(S1):S76-78",
            },
            {
                "compound_name": "Chlorogenic acid",
                "chemical_formula": "C16H18O9",
                "medicinal_use": "Reduces postprandial blood glucose; hepatoprotective; antioxidant",
                "source_study": "Ugochukwu et al. (2003), Global Journal of Pure and Applied Sciences",
            },
            {
                "compound_name": "Triterpenoid saponins",
                "chemical_formula": None,
                "medicinal_use": "Hypoglycaemic; hypolipidaemic; inhibit intestinal cholesterol absorption",
                "source_study": "Iweala & Obidoa (2009), American Journal of Biochemistry and Molecular Biology",
            },
        ],
    },
    {
        "name_english": "Oha Leaf (African Rosewood)",
        "scientific_name": "Pterocarpus mildbraedii",
        "name_igbo": "Ora (Oha)",
        "name_yoruba": None,
        "name_hausa": None,
        "description": (
            "Oha leaves are used in Igbo cuisine — most famously in oha soup — and are among the most "
            "nutritious leafy vegetables in Nigeria (up to 24% protein dry weight). Traditional medicine "
            "uses include anaemia treatment, rheumatism and convulsions."
        ),
        "region_found": "Southeastern Nigeria; Anambra, Enugu, Imo states",
        "compounds": [
            {
                "compound_name": "Pterostilbene",
                "chemical_formula": "C16H16O3",
                "medicinal_use": "Stilbenoid antioxidant; more bioavailable than resveratrol; antidiabetic and cardioprotective",
                "source_study": "McCormack & McFadden (2013), Oxidative Medicine and Cellular Longevity",
            },
            {
                "compound_name": "Catechin",
                "chemical_formula": "C15H14O6",
                "medicinal_use": "Anti-inflammatory flavonoid; promotes iron absorption; explains use in anaemia",
                "source_study": "Nwachukwu et al. (2010), Pakistan Journal of Nutrition 9(3):203-209",
            },
            {
                "compound_name": "Epicatechin",
                "chemical_formula": "C15H14O6",
                "medicinal_use": "Vasodilatory via eNOS activation; antidiabetic; neuroprotective flavonoid",
                "source_study": "Engler et al. (2004), Journal of the American College of Cardiology 43(10):1775-1782",
            },
        ],
    },
    {
        "name_english": "Uda (Negro Pepper)",
        "scientific_name": "Xylopia aethiopica",
        "name_igbo": "Uda",
        "name_yoruba": "Eeru alamo",
        "name_hausa": "Kimba",
        "description": (
            "Dried fruits are a vital spice and medicine across Nigeria and West Africa. "
            "Used postpartum to aid uterine recovery, as a galactagogue, for chest infections and as analgesic. "
            "Essential oil contains diterpenes with potent antimicrobial activity."
        ),
        "region_found": "Pan-Nigeria; wild and cultivated across rainforest zones",
        "compounds": [
            {
                "compound_name": "Xylopic acid",
                "chemical_formula": "C20H32O3",
                "medicinal_use": "Diterpene with analgesic, anti-inflammatory and antispasmodic properties; CNS depressant",
                "source_study": "Woode et al. (2009), Journal of Ethnopharmacology 126(3):522-527",
            },
            {
                "compound_name": "Kaurene",
                "chemical_formula": "C20H32",
                "medicinal_use": "Diterpene hydrocarbon with antimicrobial and antifertility activity at pharmacological doses",
                "source_study": "Ojewole & Awe (2000), Methods Findings Experimental Clinical Pharmacology",
            },
            {
                "compound_name": "Copalic acid",
                "chemical_formula": "C20H32O2",
                "medicinal_use": "Antimicrobial diterpene; active against Gram-positive bacteria and Candida species",
                "source_study": "Tairu et al. (1999), Flavour and Fragrance Journal 14(4):221-223",
            },
        ],
    },
    {
        "name_english": "Ehuru (African Nutmeg)",
        "scientific_name": "Monodora myristica",
        "name_igbo": "Ehuru",
        "name_yoruba": "Ariwo",
        "name_hausa": "Manje",
        "description": (
            "Seeds used as a spice and medicine, often as a substitute for true nutmeg. "
            "Used in Nigerian soups (ofe akwu) and as a remedy for toothache, headache, skin eruptions "
            "and rheumatism. Seed essential oil has significant antimicrobial and antioxidant activity."
        ),
        "region_found": "Southern Nigeria; rainforest belt — Edo, Delta, Rivers, Anambra states",
        "compounds": [
            {
                "compound_name": "Myristicin",
                "chemical_formula": "C11H12O3",
                "medicinal_use": "MAO-inhibitory and psychoactive at high doses; antimicrobial phenylpropanoid",
                "source_study": "Orabi et al. (1991), Phytochemistry 30(4):1349-1352",
            },
            {
                "compound_name": "Elemicin",
                "chemical_formula": "C12H16O3",
                "medicinal_use": "Anti-inflammatory, antimicrobial phenylpropanoid; precursor to psychoactive metabolites",
                "source_study": "Shulgin (1966), Nature 210:380-384",
            },
            {
                "compound_name": "Sabinene",
                "chemical_formula": "C10H16",
                "medicinal_use": "Antifungal and antioxidant monoterpene; contributes to the distinctive spice aroma",
                "source_study": "Ezeonu et al. (2012), Asian Pacific Journal of Tropical Biomedicine",
            },
        ],
    },
    {
        "name_english": "Dawadawa (African Locust Bean)",
        "scientific_name": "Parkia biglobosa",
        "name_igbo": "Ogiri / Iru",
        "name_yoruba": "Iru",
        "name_hausa": "Dawadawa",
        "description": (
            "Fermented seeds used as a condiment and traditional medicine across Nigeria. "
            "Rich in proteins and bioactive compounds produced during fermentation. Used to treat "
            "eye infections, skin conditions and hypertension. Fermentation produces ACE-inhibitory "
            "peptides relevant to blood pressure management."
        ),
        "region_found": "Pan-Nigeria; most prominent in northern and Yoruba-speaking regions",
        "compounds": [
            {
                "compound_name": "ACE-inhibitory peptides",
                "chemical_formula": None,
                "medicinal_use": "Inhibit angiotensin-converting enzyme; antihypertensive comparable to captopril in animal models",
                "source_study": "Kuba et al. (2005), Food Chemistry 91(4):657-661",
            },
            {
                "compound_name": "Beta-Sitosterol",
                "chemical_formula": "C29H50O",
                "medicinal_use": "Reduces LDL cholesterol by competing with cholesterol absorption; anti-inflammatory",
                "source_study": "Nwosu et al. (2008), Bioresource Technology 99(11):5023-5026",
            },
            {
                "compound_name": "Riboflavin (Vitamin B2)",
                "chemical_formula": "C17H20N4O6",
                "medicinal_use": "Produced in high amounts during fermentation; essential for energy metabolism and eye health",
                "source_study": "Diawara et al. (1997), International Journal of Food Sciences and Nutrition",
            },
        ],
    },
]


# ---------------------------------------------------------------------------
# Seed function
# ---------------------------------------------------------------------------

def seed_herbs(db) -> int:
    """Insert herbs if table is empty. Returns count inserted (0 if already seeded)."""
    from app.models.herb import Herb
    from app.models.herb_compound import HerbCompound

    if db.query(Herb).count() > 0:
        print("Herbs table already contains data — skipping seed.")
        return 0

    inserted = 0
    for raw in HERBS_DATA:
        data = dict(raw)
        compounds_data = data.pop("compounds", [])
        herb = Herb(**data)
        db.add(herb)
        db.flush()
        for c in compounds_data:
            db.add(HerbCompound(herb_id=herb.id, **c))
        inserted += 1

    db.commit()
    print(f"Seeded {inserted} herbs with their compounds.")
    return inserted


# ---------------------------------------------------------------------------
# Standalone entry-point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
    from app.core.database import SessionLocal

    db = SessionLocal()
    try:
        seed_herbs(db)
    finally:
        db.close()
