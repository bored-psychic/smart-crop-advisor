"""
Canonical disease + pest database — 26+ crops, 50+ entries.
Single source of truth. Imported by both backend (routers/disease.py)
and frontend (tab2_disease.py).
"""

DISEASE_DB: dict[str, dict[str, dict]] = {
    'Tomato': {
        'Yellow leaves + brown spots': {'disease': 'Early Blight (Alternaria solani)', 'treatment': 'Mancozeb 75% WP @ 2g/L. Remove infected leaves. Repeat after 10 days.', 'prevention': 'Crop rotation every 2 years. Use resistant varieties.', 'severity': 'Medium', 'type': 'Disease'},
        'Dark brown patches + white mold undersides': {'disease': 'Late Blight (Phytophthora infestans)', 'treatment': 'Metalaxyl + Mancozeb @ 2g/L immediately. Destroy infected plants.', 'prevention': 'Avoid overhead irrigation. Certified disease-free seeds.', 'severity': 'High', 'type': 'Disease'},
        'Curling yellow leaves + stunted growth': {'disease': 'Tomato Yellow Leaf Curl Virus', 'treatment': 'No cure. Remove infected plants immediately.', 'prevention': 'Control whitefly. Silver reflective mulch.', 'severity': 'High', 'type': 'Disease'},
        'Small dark spots with yellow halo': {'disease': 'Bacterial Spot (Xanthomonas)', 'treatment': 'Copper hydroxide @ 3g/L every 7 days.', 'prevention': 'Disease-free transplants. Avoid wet fieldwork.', 'severity': 'Medium', 'type': 'Disease'},
        'White powdery coating on leaves': {'disease': 'Powdery Mildew (Leveillula taurica)', 'treatment': 'Sulphur 80% WP @ 2g/L or Hexaconazole.', 'prevention': 'Improve air circulation. Avoid excess nitrogen.', 'severity': 'Low', 'type': 'Disease'},
        'Tiny white flying insects under leaves': {'disease': 'Whitefly (Bemisia tabaci)', 'treatment': 'Buprofezin 25 SC @ 1.0 L/ha or Diafenthiuron 50 WP. Neem oil 0.5%.', 'prevention': 'Yellow sticky traps. Silver reflective mulch. Remove infested leaves.', 'severity': 'Medium', 'type': 'Pest'},
        'Mines/tunnels in leaves': {'disease': 'Serpentine Leaf Miner (Liriomyza trifolii)', 'treatment': 'Cyantraniliprole 10.26 OD @ 15ml/10L or Spinosad 45 SC @ 0.3ml/L.', 'prevention': 'Remove heavily mined leaves. Use yellow sticky traps.', 'severity': 'Medium', 'type': 'Pest'},
    },
    'Potato': {
        'Brown lesions with yellow border on leaves': {'disease': 'Early Blight (Alternaria solani)', 'treatment': 'Chlorothalonil @ 2g/L. Repeat every 10 days.', 'prevention': 'Certified seed tubers. Crop rotation.', 'severity': 'Medium', 'type': 'Disease'},
        'Water-soaked dark patches spreading fast': {'disease': 'Late Blight (Phytophthora infestans)', 'treatment': 'Cymoxanil + Mancozeb urgently. Destroy infected haulms.', 'prevention': 'Well-drained soil. Monitor weather.', 'severity': 'High', 'type': 'Disease'},
        'Yellowing from bottom leaves upward': {'disease': 'Potato Virus Y (PVY)', 'treatment': 'No cure. Rogue out infected plants.', 'prevention': 'Virus-free seed. Control aphid vectors.', 'severity': 'High', 'type': 'Disease'},
    },
    'Rice': {
        'Diamond-shaped lesions with grey center': {'disease': 'Rice Blast (Magnaporthe oryzae)', 'treatment': 'Tricyclazole 75% WP @ 0.6g/L at booting stage.', 'prevention': 'Blast-resistant varieties. Avoid excess nitrogen.', 'severity': 'High', 'type': 'Disease'},
        'Yellow-orange stripes on leaf margins': {'disease': 'Bacterial Leaf Blight (Xanthomonas oryzae)', 'treatment': 'Copper-based bactericide. Drain fields temporarily.', 'prevention': 'Resistant varieties. Balanced fertilization.', 'severity': 'High', 'type': 'Disease'},
        'Brown spots with yellow halo': {'disease': 'Brown Spot (Cochliobolus miyabeanus)', 'treatment': 'Mancozeb or Iprodione fungicide.', 'prevention': 'Balanced K nutrition. Healthy seeds.', 'severity': 'Medium', 'type': 'Disease'},
        'Dead heart / wilting tillers': {'disease': 'Yellow Stem Borer (Scirpophaga incertulas)', 'treatment': 'Cartap Hydrochloride 4G @ 12-15 kg/ha. NSKE 5%.', 'prevention': 'Pheromone traps. Avoid excess nitrogen.', 'severity': 'High', 'type': 'Pest'},
        'Yellowing + plant collapse (hopperburn)': {'disease': 'Brown Planthopper (Nilaparvata lugens)', 'treatment': 'Pymetrozine 50 WG @ 200g/ha or Buprofezin 25 SC @ 1.0 L/ha.', 'prevention': 'Resistant varieties. Avoid excess nitrogen. Light traps.', 'severity': 'High', 'type': 'Pest'},
        'Leaves folded lengthwise with feeding damage': {'disease': 'Leaf Folder (Cnaphalocrocis medinalis)', 'treatment': 'Chlorantraniliprole 18.5 SC @ 150 ml/ha or Bt spray.', 'prevention': 'Light traps. Avoid continuous flooding.', 'severity': 'Medium', 'type': 'Pest'},
    },
    'Maize': {
        'Orange powdery pustules on leaves': {'disease': 'Common Rust (Puccinia sorghi)', 'treatment': 'Mancozeb or Azoxystrobin @ 1ml/L.', 'prevention': 'Rust-resistant hybrids. Early planting.', 'severity': 'Medium', 'type': 'Disease'},
        'Long grey-green lesions on leaves': {'disease': 'Northern Leaf Blight (Exserohilum turcicum)', 'treatment': 'Propiconazole fungicide at early stage.', 'prevention': 'Resistant varieties. Crop rotation.', 'severity': 'Medium', 'type': 'Disease'},
        'Galls/tumors on plant parts': {'disease': 'Common Smut (Ustilago maydis)', 'treatment': 'No chemical cure. Remove and destroy galls before they burst.', 'prevention': 'Avoid mechanical injury. Seed treatment.', 'severity': 'Medium', 'type': 'Disease'},
        'Ragged leaf feeding + frass in whorl': {'disease': 'Fall Armyworm (Spodoptera frugiperda)', 'treatment': 'Chlorantraniliprole 18.5 SC @ 0.4ml/L or Spinetoram 11.7 SC @ 0.5ml/L.', 'prevention': 'Pheromone traps. Early sowing. Intercrop with beans.', 'severity': 'High', 'type': 'Pest'},
    },
    'Wheat': {
        'Yellow stripes along leaf veins': {'disease': 'Yellow/Stripe Rust (Puccinia striiformis)', 'treatment': 'Propiconazole 25% EC @ 1ml/L urgently.', 'prevention': 'Resistant varieties. Early sowing.', 'severity': 'High', 'type': 'Disease'},
        'Orange-brown pustules scattered on leaves': {'disease': 'Brown/Leaf Rust (Puccinia triticina)', 'treatment': 'Tebuconazole or Propiconazole fungicide.', 'prevention': 'Balanced nitrogen. Tolerant varieties.', 'severity': 'Medium', 'type': 'Disease'},
        'Black powdery pustules on stems': {'disease': 'Stem/Black Rust (Puccinia graminis)', 'treatment': 'Mancozeb + Propiconazole immediately.', 'prevention': 'Ug99-resistant varieties. Early detection critical.', 'severity': 'High', 'type': 'Disease'},
    },
    'Cotton': {
        'Wilting + internal stem discoloration': {'disease': 'Fusarium Wilt (Fusarium oxysporum)', 'treatment': 'No cure. Remove infected plants. Soil solarization.', 'prevention': 'Wilt-resistant varieties. Crop rotation with cereals.', 'severity': 'High', 'type': 'Disease'},
        'Angular water-soaked leaf spots': {'disease': 'Bacterial Blight (Xanthomonas citri)', 'treatment': 'Copper oxychloride @ 3g/L. Avoid overhead irrigation.', 'prevention': 'Certified disease-free seeds. Balanced nutrition.', 'severity': 'Medium', 'type': 'Disease'},
        'Pink larvae inside bolls': {'disease': 'Pink Bollworm (Pectinophora gossypiella)', 'treatment': 'Chlorpyrifos 50% + Cypermethrin 5% EC @ 2ml/L. PBW pheromone traps.', 'prevention': 'Destroy crop residue. Pheromone traps early in season.', 'severity': 'High', 'type': 'Pest'},
        'Small greenish insects on tender shoots': {'disease': 'Cotton Aphid (Aphis gossypii)', 'treatment': 'Acetamiprid 20 SP @ 50g/ha or Imidacloprid 17.8 SL.', 'prevention': 'Natural enemies (ladybird beetles). Avoid excess nitrogen.', 'severity': 'Medium', 'type': 'Pest'},
        'Wedge-shaped insects jumping when disturbed': {'disease': 'Cotton Jassid / Leafhopper (Amrasca biguttula)', 'treatment': 'Acetamiprid 20 SP @ 50-60g/ha or Fipronil 5 SC.', 'prevention': 'Hairy varieties. Monitor from seedling stage.', 'severity': 'Medium', 'type': 'Pest'},
        'Greenish caterpillar eating bolls and flowers': {'disease': 'Cotton Bollworm (Helicoverpa armigera)', 'treatment': 'Indoxacarb 14.5 SC @ 1ml/L or Spinosad 45 SC @ 0.4ml/L.', 'prevention': 'Pheromone traps. Intercropping with pigeonpea.', 'severity': 'High', 'type': 'Pest'},
    },
    'Banana': {
        'Yellow streaks on young leaves': {'disease': 'Banana Bunchy Top Virus (BBTV)', 'treatment': 'No cure. Destroy infected plants immediately.', 'prevention': 'Virus-free tissue culture plants. Control aphids.', 'severity': 'High', 'type': 'Disease'},
        'Black streaks inside stem + wilting': {'disease': 'Panama Wilt / Fusarium Wilt', 'treatment': 'No chemical cure. Destroy infected plants.', 'prevention': 'Resistant Cavendish varieties. Clean tools.', 'severity': 'High', 'type': 'Disease'},
    },
    'Chickpea': {
        'Wilting + brown discoloration at soil level': {'disease': 'Fusarium Wilt', 'treatment': 'Seed treatment with Carbendazim 2g/kg.', 'prevention': 'Resistant varieties. Deep summer ploughing.', 'severity': 'High', 'type': 'Disease'},
        'Angular water-soaked spots on pods/leaves': {'disease': 'Ascochyta Blight', 'treatment': 'Mancozeb 75% WP @ 2g/L.', 'prevention': 'Certified disease-free seed.', 'severity': 'High', 'type': 'Disease'},
        'Greenish caterpillar boring into pods': {'disease': 'Gram Pod Borer (Helicoverpa armigera)', 'treatment': 'Indoxacarb 14.5 SC @ 1ml/L. NPV @ 250 LE/ha.', 'prevention': 'Pheromone traps. Intercropping with coriander.', 'severity': 'High', 'type': 'Pest'},
    },
    'Groundnut': {
        'Circular brown spots with yellow halo': {'disease': 'Early Leaf Spot', 'treatment': 'Chlorothalonil or Mancozeb @ 2g/L.', 'prevention': 'Crop rotation. Remove crop debris.', 'severity': 'Medium', 'type': 'Disease'},
        'Dark brown to black spots without halo': {'disease': 'Late Leaf Spot', 'treatment': 'Carbendazim 50 WP @ 1g/L.', 'prevention': 'Resistant varieties. Balanced nutrition.', 'severity': 'Medium', 'type': 'Disease'},
        'Gregarious caterpillars skeletonizing leaves': {'disease': 'Tobacco Caterpillar (Spodoptera litura)', 'treatment': 'Chlorantraniliprole 18.5 SC @ 150 ml/ha.', 'prevention': 'Pheromone traps. Hand-picking egg masses.', 'severity': 'High', 'type': 'Pest'},
    },
    'Soybean': {
        'Reddish-brown pustules on leaf undersides': {'disease': 'Soybean Rust', 'treatment': 'Azoxystrobin + Propiconazole @ 1ml/L urgently.', 'prevention': 'Monitor from flowering.', 'severity': 'High', 'type': 'Disease'},
        'Brown caterpillar defoliating leaves': {'disease': 'Tobacco Caterpillar', 'treatment': 'Chlorantraniliprole 18.5 SC @ 150 ml/ha.', 'prevention': 'Pheromone traps.', 'severity': 'High', 'type': 'Pest'},
    },
    'Mustard': {
        'Greenish-yellow aphids on pods + leaves': {'disease': 'Mustard Aphid', 'treatment': 'Dimethoate 30 EC @ 300-500 ml/ha.', 'prevention': 'Early sowing.', 'severity': 'High', 'type': 'Pest'},
        'Yellowing + white rust pustules': {'disease': 'White Rust (Albugo candida)', 'treatment': 'Mancozeb 75% WP @ 2g/L.', 'prevention': 'Resistant varieties.', 'severity': 'Medium', 'type': 'Disease'},
    },
    'Sugarcane': {
        'Red rot inside stalk (vinegar smell)': {'disease': 'Red Rot', 'treatment': 'No chemical cure. Use disease-free setts.', 'prevention': 'Resistant varieties. Hot water treatment of setts.', 'severity': 'High', 'type': 'Disease'},
        'White woolly aphids on leaves': {'disease': 'Sugarcane Woolly Aphid', 'treatment': 'Buprofezin 25 SC @ 1.0 L/ha.', 'prevention': 'Conserve natural enemies.', 'severity': 'Medium', 'type': 'Pest'},
    },
    'Mango': {
        'Mummified blackened inflorescences': {'disease': 'Mango Malformation', 'treatment': 'Remove and destroy malformed parts.', 'prevention': 'Certified nursery plants.', 'severity': 'High', 'type': 'Disease'},
        'Small jumping insects on flowers': {'disease': 'Mango Hopper', 'treatment': 'Imidacloprid 17.8 SL @ 100 ml/ha.', 'prevention': 'Spray at bud burst and flowering.', 'severity': 'High', 'type': 'Pest'},
        'Maggot in fruit (puncture marks on skin)': {'disease': 'Fruit Fly (Bactrocera dorsalis)', 'treatment': 'Methyl eugenol traps. Spinosad bait spray.', 'prevention': 'Collect and destroy fallen fruit daily.', 'severity': 'High', 'type': 'Pest'},
    },
    'Brinjal': {
        'Wilting shoot tips + fruit bored': {'disease': 'Shoot and Fruit Borer', 'treatment': 'Emamectin benzoate 5% SG @ 4g/10L.', 'prevention': 'Remove bored shoots weekly.', 'severity': 'High', 'type': 'Pest'},
        'Purplish lesions on stem': {'disease': 'Phomopsis Blight', 'treatment': 'Carbendazim + Mancozeb.', 'prevention': 'Crop rotation.', 'severity': 'High', 'type': 'Disease'},
    },
    'Chilli': {
        'Galls on flower buds': {'disease': 'Chilli Gall Midge', 'treatment': 'Fipronil 5 SC @ 1.5 L/ha.', 'prevention': 'Early detection.', 'severity': 'Medium', 'type': 'Pest'},
        'Leaf curl + fruit deformation': {'disease': 'Chilli Leaf Curl Virus', 'treatment': 'No cure. Remove infected plants.', 'prevention': 'Use certified seedlings.', 'severity': 'High', 'type': 'Disease'},
    },
    'Cabbage': {
        'Diamond-shaped holes + small worms': {'disease': 'Diamondback Moth', 'treatment': 'Chlorantraniliprole 18.5 SC @ 150 ml/ha.', 'prevention': 'Rotation with non-Brassica crops.', 'severity': 'High', 'type': 'Pest'},
        'Slimy black rot at leaf margins': {'disease': 'Black Rot (Xanthomonas campestris)', 'treatment': 'Copper hydroxide 53.8 WP @ 2g/L.', 'prevention': 'Certified disease-free seed.', 'severity': 'High', 'type': 'Disease'},
    },
    'Apple': {
        'Olive-green scab on leaves and fruit': {'disease': 'Apple Scab', 'treatment': 'Captan 50% WP @ 2g/L.', 'prevention': 'Resistant varieties.', 'severity': 'Medium', 'type': 'Disease'},
        'Brown/black cankers on fruit': {'disease': 'Apple Black Rot', 'treatment': 'Captan or Thiophanate-methyl.', 'prevention': 'Prune infected branches.', 'severity': 'High', 'type': 'Disease'},
    },
    'Grape': {
        'Downy white growth on leaf undersides': {'disease': 'Downy Mildew', 'treatment': 'Metalaxyl + Mancozeb @ 2g/L.', 'prevention': 'Prune for airflow.', 'severity': 'High', 'type': 'Disease'},
        'Powdery white coating on young shoots': {'disease': 'Powdery Mildew', 'treatment': 'Sulphur 80 WP @ 3g/L.', 'prevention': 'Prune dense canopy.', 'severity': 'Medium', 'type': 'Disease'},
    },
    'Coconut': {
        'Crown rot + bud death': {'disease': 'Bud Rot', 'treatment': 'Bordeaux mixture 1% into crown.', 'prevention': 'Avoid water stagnation.', 'severity': 'High', 'type': 'Disease'},
    },
    'Coffee': {
        'Orange powdery pustules on leaf undersides': {'disease': 'Coffee Leaf Rust', 'treatment': 'Copper hydroxide or Propiconazole.', 'prevention': 'Rust-resistant varieties.', 'severity': 'High', 'type': 'Disease'},
    },
    'Stored Grains': {
        'Small reddish-brown weevils in grain': {'disease': 'Rice/Maize Weevil', 'treatment': 'Malathion 5% Dust or Phosphine fumigation.', 'prevention': 'Clean storage. Moisture <13%.', 'severity': 'High', 'type': 'Pest'},
        'Small cylindrical brown beetles': {'disease': 'Lesser Grain Borer', 'treatment': 'Deltamethrin 2.8 EC.', 'prevention': 'Clean storage. Mix with neem leaves.', 'severity': 'High', 'type': 'Pest'},
        'Webbing + caterpillars in stored grain': {'disease': 'Indian Meal Moth', 'treatment': 'Bt spray. Pheromone traps.', 'prevention': 'Sealed storage.', 'severity': 'Medium', 'type': 'Pest'},
        'Small brownish beetles in stored pulses': {'disease': 'Pulse Beetle', 'treatment': 'Neem oil coating 5 ml/kg seed.', 'prevention': 'Sun-dry grain before storage.', 'severity': 'Medium', 'type': 'Pest'},
    },
    'Pigeonpea': {
        'Wilting + dry root rot': {'disease': 'Fusarium Wilt', 'treatment': 'Seed treatment with Trichoderma viride.', 'prevention': 'Resistant varieties.', 'severity': 'High', 'type': 'Disease'},
    },
    'Lentil': {
        'Grey mold on stems and pods': {'disease': 'Botrytis Grey Mold', 'treatment': 'Carbendazim 50 WP @ 1g/L.', 'prevention': 'Avoid dense planting.', 'severity': 'Medium', 'type': 'Disease'},
    },
    'Papaya': {
        'Mosaic + leaf distortion': {'disease': 'Papaya Ring Spot Virus', 'treatment': 'No cure. Destroy infected plants.', 'prevention': 'Certified virus-free seedlings.', 'severity': 'High', 'type': 'Disease'},
    },
    'Orange': {
        'Yellow mottling + leaf drop': {'disease': 'Citrus Greening / HLB', 'treatment': 'No cure. Remove infected trees.', 'prevention': 'Certified nursery plants. Control psyllid.', 'severity': 'High', 'type': 'Disease'},
    },
    'Watermelon': {
        'Powdery white patches on leaves': {'disease': 'Powdery Mildew', 'treatment': 'Sulphur 80 WP @ 2g/L.', 'prevention': 'Resistant varieties.', 'severity': 'Low', 'type': 'Disease'},
    },
    'Jute': {
        'Black ants on stem + tunneling': {'disease': 'Jute Semilooper', 'treatment': 'Malathion 50 EC @ 1ml/L.', 'prevention': 'Early sowing. Remove weeds.', 'severity': 'Medium', 'type': 'Pest'},
    },
}
