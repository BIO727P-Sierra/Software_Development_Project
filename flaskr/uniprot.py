from flask import Flask, render_template, url_for, redirect, flash, session, Blueprint
from .uniprotAPI import retrieve_protein_sequence_features
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import InputRequired
from .uniprot_classes import UniprotProtein, UniprotFeatures
from . import db

### PAULA's EDIT - ADDING flask_login PACKAGE. LOGGED IN USERS CAN ONLY ACCESS ###

from flask_login import login_required

###########################################

bp = Blueprint('uniprot', __name__, url_prefix='/uniprot')

# Obtain uniprot ID from user input
class QueryForm(FlaskForm):
	uniprot_id = StringField('Enter UniProt ID:', validators=[InputRequired()])
	submit = SubmitField('Submit')
     
# Url for obtaining uniprot data
@bp.route("/", methods=["GET", "POST"]) 
@login_required                           #This added route makes logged in users have access only to the feature
def uniprot_search():
	form = QueryForm()  # Create form to pass to template
	uniprot_id = None
	if form.validate_on_submit():
		uniprot_id = form.uniprot_id.data
		uniprot_data = retrieve_protein_sequence_features(uniprot_id)
		if uniprot_data[0] != None:
			aminoacid_sequence, features_type_location = uniprot_data
            #Store uniprot data for next page review and confirmation before sql database storage
			session["uniprot_id"] = uniprot_id
			session["aminoacid_sequence"] = aminoacid_sequence
			session["features_type_location"] = features_type_location
			return redirect(url_for('uniprot.confirmation'))
		elif uniprot_data[0] == None:
			flash(uniprot_data[1])
			return redirect(url_for('uniprot.uniprot_search'))
	return render_template('uniprot/uniprot_search.html', form=form)

# This will review information about the uniprot protein before user confirmation and storage to sql database
@bp.route("/confirmation", methods=["GET", "POST"])
@login_required                                         #Added route allows logged in user to access this feature
def confirmation():
	# If confirmed, store uniprot data to sql database and redirect to plasmid upload page
	uniprot_id = session.get("uniprot_id")
	aminoacid_sequence = session.get("aminoacid_sequence") 
	features_type_location = session.get("features_type_location")
	return render_template('uniprot/uniprot_review.html', uniprot_id=uniprot_id, aminoacid_sequence=aminoacid_sequence, features_type_location=features_type_location)

@bp.route("/data-stored", methods=["GET", "POST"])
@login_required                                         #Added route allows logged in user to access this feature
def data_stored():
	uniprot_id = session.get("uniprot_id")
	aminoacid_sequence = session.get("aminoacid_sequence") 
	features_type_location = session.get("features_type_location")
	protein = UniprotProtein(uniprot_id=uniprot_id, wt_protein_sequence=aminoacid_sequence)
	# Add features to protein
	for f in features_type_location:
		feature = UniprotFeatures(
			uniprot_features=f['feature_type'],
			feature_start_location=f['start_location'],
			feature_end_location =f['end_location']
		)
		protein.features.append(feature)
	
	db.session.add(protein)
	db.session.commit()
	
	return 'UPLOAD PLASMID' 
