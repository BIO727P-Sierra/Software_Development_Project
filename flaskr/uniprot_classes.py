from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text

# SQL schema for inserting uniprot data
db = SQLAlchemy()

# Schema for uniprot protein ID and sequence
class UniprotProtein(db.Model):
    __tablename__ = 'uniprot_proteins'
    #experiment_id = db.Column(db.Integer, db.ForeignKey("experiments.experiment_id", ondelete="CASCADE"), nullable=False)
    uniprot_id = db.Column(db.String(20), nullable=False, primary_key=True)
    wt_protein_sequence = db.Column(db.Text, nullable=False)

    def __repr__(self):
        return f"<Experiment {self.experiment_id}>"

class UniprotFeatures(db.Model):
    __tablename__ = 'uniprot_features'
    feature_id = db.Column(db.Integer, primary_key=True)  
    uniprot_id = db.Column(db.String(20), db.ForeignKey("uniprot_proteins.uniprot_id", ondelete="CASCADE"), nullable=False)
    uniprot_features = db.Column(db.Text, nullable=False)
    feature_start_location = db.Column(db.Integer, nullable=False)
    feature_end_location = db.Column(db.Integer, nullable=False)
    
    def __repr__(self):
        return f"<UniprotFeature {self.uniprot_id}>"




# Define relationships between UniprotProtein and UniprotFeatures
UniprotProtein.features = db.relationship(
    "UniprotFeatures",
    back_populates="protein",
    cascade="all, delete-orphan"
)

UniprotFeatures.protein = db.relationship(
    "UniprotProtein", 
    back_populates="features"
)