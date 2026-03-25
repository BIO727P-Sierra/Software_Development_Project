import requests

# Retrieve protein sequence and feature based on uniprot id
def retrieve_protein_sequence_features(uniprot_id):
    # Base url for uniprot API
    uniprot_url = f'https://rest.uniprot.org/uniprotkb/{uniprot_id}'
    # Test if uniprot ID is valid
    entry_url = f'{uniprot_url}.txt'
    entry_response = requests.get(entry_url)
    try:
        if entry_response.ok == False:
            return None, f"Invalid Uniprot ID. Error code: {entry_response.status_code}"
    except requests.RequestException as e:
        return None, f"Error: {e}"
    
    # Retrieve amino acid sequence in fasta format 
    sequence_url = f'{uniprot_url}.fasta'
    try:
        fasta_response = requests.get(sequence_url)
        if fasta_response.ok:
            sequence_fasta = fasta_response.text
        else:
            return None, "Fasta sequence access failed"
    except requests.RequestException as e:
        return None, f"Error: {e}"
    aminoacid_sequence = ''.join(sequence_fasta.split('\n')[1:])    # Removes header and joins sequences separated by new lines

    # Filter json for feature details - removes some info such as publishing/ annotation dates, comments etc.
    json_filter = '?fields=protein_name,organism_name,ft_var_seq%2Cft_variant%2Cft_non_cons%2Cft_non_std%2Cft_non_ter%2Cft_conflict%2Cft_unsure%2Cft_act_site%2Cft_binding%2Cft_dna_bind%2Cft_site%2Cft_mutagen%2Cft_intramem%2Cft_topo_dom%2Cft_transmem%2Cft_chain%2Cft_crosslnk%2Cft_disulfid%2Cft_carbohyd%2Cft_init_met%2Cft_lipid%2Cft_mod_res%2Cft_peptide%2Cft_propep%2Cft_signal%2Cft_transit%2Cft_strand%2Cft_helix%2Cft_turn%2Cft_coiled%2Cft_compbias%2Cft_domain%2Cft_motif%2Cft_region%2Cft_repeat%2Cft_zn_fing'
    # Retrieve features in json format
    feature_url = f'{uniprot_url}.json{json_filter}'
    try:
        json_response = requests.get(feature_url)
        if json_response.ok:
            feature_json = json_response.json()
            protein_name = feature_json["proteinDescription"]["recommendedName"]["fullName"]["value"]    # Name of protein
            organism_name = feature_json["organism"]["scientificName"]    # Scientific name of organism 
        else:
            return None, 'Feature access failed'
    except requests.RequestException as e:
        return None, f"Error: {e}"

    # Retrieve names/function and location of key domains from feature json to store into sql database
    features_list = feature_json['features']
    features_type_location = []
    for feature in features_list:
        feature_dict = {}
        description = feature['description']    # Description of features e.g. location or function
        type = feature['type']    # Type of feature e.g. peptide, helix, disulfide bond
        start, end = [feature['location']['start']['value'], feature['location']['end']['value']]    # Start and end position based on amino acid sequence 
        if description == '':
            feature_dict['feature_type'] = type
        else:
            feature_dict['feature_type'] = f'{type} - {description}'
        feature_dict['start_location'] = start
        feature_dict['end_location'] = end
        features_type_location += [feature_dict]


    return aminoacid_sequence, features_type_location, protein_name, organism_name # Need to add data to SQL database except protein name and organism name for review
