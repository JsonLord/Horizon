from pathlib import Path
from src.research.reporting import atomic,dumps
from src.research.radar.contracts import Digest,RadarManifest
from src.research.radar.pipeline import State,TechnicalFinding
if __name__=='__main__':
    for name,model in [('radar-digest',Digest),('radar-manifest',RadarManifest),('radar-state',State),('radar-finding',TechnicalFinding)]:
        atomic(Path('schemas')/(name+'.schema.json'),dumps(model.model_json_schema()))
