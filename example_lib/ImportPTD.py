from pyrevit import forms
from Tendon import Tendon
from TendonSet import TendonSet

class ImportTendonsText:
	def __init__(self, file_path):
		self.file_path = file_path

	def coordinates(self, val):
		raw = val.split(",")
		return ( float(raw[0][1:]), float(raw[1][:-1]) )

	def process(self):
		table_active= False
		tendon_active=None
		dataset = TendonSet()
		try:
			with open(self.file_path) as file:
				for line in file:
					line = line.rstrip()       
			 
					if not tendon_active and line.startswith("Tendon No.") :                
						tid = int(line.split("Tendon No.")[1].strip()) 
						tendon_active = Tendon(ID=tid)

					if not tendon_active:
						continue
					#get the tendon Length
					if line.startswith("Length"):
						length = float(line.split(":")[1].strip()[:-1])
						tendon_active.length = tendon_active.mtryrd_set( length )
					#get the tendon co-orinates    
					if line.startswith("End Point co-orinates,"):
						raw_start = line.split("start:")[1].split("end:")[0].strip()
						raw_end = line.split("end:")[1].strip()
						tendon_active.start = tendon_active.set_coordinates( self.coordinates(raw_start) )
						tendon_active.end = tendon_active.set_coordinates( self.coordinates(raw_end) )
					#get the tendon Type
					if line.startswith("Type    "):
						tendon_active.tendon_type = int(line.split(":")[1].strip())
						
						#get the tendon type of strands
					if line.startswith("Type of strands"):
						tendon_active.strand_type = float(line.split(":")[1].strip())
						#get the tendon number of strands
					if line.startswith("Number of strands"):
						tendon_active.strand_no = int(line.split(":")[1].strip())

					if "No.," in line and "H:5mm" in line:
						table_active= True
						continue        

					if tendon_active and table_active:
						if not line:
							table_active= False
							clean_points = []
							for i, tp in enumerate(tendon_active.tendon_points):
								if i == 0:
									clean_points.append( [tendon_active.mtryrd_set(tp[1]), int(tp[4] * 1000)] )
								elif i == len(tendon_active.tendon_points)-1:
									clean_points.append( [tendon_active.mtryrd_set(tp[1]), int(tp[4] * 1000)] )
								else:
									clean_points.append( [tendon_active.mtryrd_set(tp[1]), int(tp[3] * 1000)] )
							tendon_active.tendon_points= list(clean_points)
							dataset.append(tendon_active)
							tendon_active = None
							continue
						if not tendon_active.tendon_points:
							tendon_active.tendon_points = []            
						row = line.split(",")             
						tendon_active.tendon_points.append([float(c.strip()) for c in row if c.strip()])
			return dataset
		except Exception as ex:
			print("failed to process import")
			forms.alert(str(ex), title='Error')	