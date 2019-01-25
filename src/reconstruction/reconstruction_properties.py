from cobamp.utilities.property_management import PropertyDictionary
from cobamp.wrappers.external_wrappers import model_readers

from reconstruction.methods_reconstruction import MethodsReconstruction


class PropertiesReconstruction(PropertyDictionary):
	def __init__(self):
		self.base_mandatory = {'solver': str, 'template_model': model_readers, 'method': MethodsReconstruction,
							   'omics_type': 'omics'}
		self.base_optional = {'env_conditions': dict, 'flux_threshold': float}
		super().__init__(self.base_mandatory, self.base_optional)


class FastcoreProperties(PropertiesReconstruction):
	def __init__(self, core, flux_threshold=1e-4):
		new_mandatory = {'core': lambda x: isinstance(x, list) and len(x) > 0,
						 'core_idx': lambda x: isinstance(x, list) and len(x) > 0}
		new_optional = {}
		super().__init__()
		self.base_mandatory['method'] = MethodsReconstruction.FASTCORE
		self.add_new_properties(new_mandatory, new_optional)
		self['flux_threshold'] = flux_threshold
		self['core'] = core
		#TODO change this later, this is only for testing
		self['core_idx'] = core
		# self['core_idx'] = [model_readers.reaction_id_to_index(reaction) for reaction in core]

class GIMMEProperties(PropertiesReconstruction):
	def __init__(self, exp_vector, objectives, obj_frac=0.9, preprocess=False, flux_threshold=None):
		new_mandatory = {
			'exp_vector': lambda x: isinstance(x, list) and len(x) > 0 or isinstance(x, ndarray),
			'preprocess': lambda x: isinstance(x, bool) or x is None,
			'objectives': lambda x: type(x) in [list, ndarray]}
		new_optional = {'obj_frac': lambda x: type(x) in [ndarray, list, tuple, float]}
		super().__init__()

		self.add_new_properties(new_mandatory, new_optional)

		self['objectives'] = objectives
		self['exp_vector'] = exp_vector
		self['obj_frac'] = obj_frac if isinstance(obj_frac, ndarray) else array([obj_frac]*len(objectives))
		self['preprocess'] = True if preprocess else False
		self['flux_threshold'] = 1e-4 if flux_threshold is None else flux_threshold

if __name__ == '__main__':
	properties = PropertiesReconstruction()
	print(properties.get_mandatory_properties())
	pro = FastcoreProperties(['a', 'b', 'c'])
	print(pro.get_mandatory_properties())
	pro.has_required_properties()
	pro['core']
