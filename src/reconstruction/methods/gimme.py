import numpy as np

from cobamp.core.linear_systems import SteadyStateLinearSystem
from cobamp.core.optimization import LinearSystemOptimizer

class GIMME():
	def __init__(self, S, lb, ub, properties):
		self.S = S
		self.lb, self.ub = lb, ub
		self.properties = properties

	def preprocess(self):

		if 'obj_frac' not in self.properties:
			self.properties['obj_frac'] = 0.9

		exp_rxns = self.properties['expression_rxns']
		obj_exps = self.properties['objectives']

		M,N = self.S.shape

		## make irreversible model
		Sn, lb_n, ub_n, irrev_mapping = self.make_irreversible(S, lb, ub)

		## check for expression data size
		exp_vector = np.zeros(Sn.shape[1],)
		for rxn, val in exp_rxns.items():
			rxmap = irrev_mapping[rxn]
			if isinstance(rxmap, tuple):
				exp_vector[rxmap[0]] = exp_vector[rxmap[1]] = val

		## adjust objectives for irreversible model
		objectives = [self.adjust_objective_to_irreversible(Sn, obj) for obj in obj_exps]

		return Sn, np.array(lb_n), np.array(ub_n), irrev_mapping, exp_vector, objectives

	def run(self):

		obj_frac = self.properties['obj_frac']
		flux_thres = self.properties['flux_threshold']

		S, lb, ub, irrev_mapping, exp_vector, objectives = self.preprocess()
		M,N = S.shape
		## FBA for each objective
		lsystem = SteadyStateLinearSystem(S, lb, ub, ['V'+str(i) for i in range(S.shape[1])])
		lso = LinearSystemOptimizer(lsystem)

		def find_objective_value(obj):
			lsystem.set_objective(obj, False)
			sol = lso.optimize()
			return sol.objective_value() ## TODO: Must implement

		objective_values = list(map(find_objective_value, objectives))

		gimme_model_objective = np.array([flux_thres - exp_vector[i] if -1 < exp_vector[i] < flux_thres else 0 for i in range(N)])

		objective_lbs = sum(list(map(lambda a,b: a*b, objectives, objective_values)))
		objective_ids = np.nonzero(objective_lbs)[0]
		lb[objective_ids] = objective_lbs[objective_ids]

		gimme_system = SteadyStateLinearSystem(S, lb, ub, var_names=['GIMME'+str(i) for i in range(N)])
		gimme_lso = LinearSystemOptimizer(gimme_system)
		gimme_system.set_objective(gimme_model_objective)

		gimme_solution = gimme_lso.optimize()

		reaction_activity_irrev_model = self.get_reaction_activity(gimme_solution, exp_vector, flux_thres)
		reaction_activity_original = [np.max(reaction_activity_irrev_model[new]) for orig, new in irrev_mapping]

		return reaction_activity_original



	def adjust_objective_to_irreversible(self, S_new, objective, mapping):
		objective_new = np.zeros(S_new.shape[1],)
		nzids = np.nonzero(objective)[0]
		for id in nzids:
			objective_new[mapping[id]] = objective[id]
		return objective_new

	def make_irreversible(self, S, lb, ub):
		irrev = np.array([i for i in range(self.S.shape[1]) if not (lb[i] < 0 and ub[i] > 0)])
		Si, Sr = S[:,irrev], S[:,-irrev]
		offset = Si.shape[1]

		rx_mapping.update({ii:(offset+n, offset+n+Sr.shape[1]) for n,ii in enumerate([i for i in range(S.shape[1]) if i not in irrev])]})
		rx_mapping.update(irrev_mapping)

		S_new = np.hstack([Si, Sr, -Sr])
		nlb, nub = np.zeros(S_new.shape[1])
		for orig_rx, new_rx in rx_mapping.items():
			if isinstance(new_rx, tuple):
				nub[new_rx[0]] = lb[orig_rx]
				nub[new_rx[1]] = ub[orig_rx]
			else:
				nlb[new_rx], nub[new_rx] = lb[orig_rx], ub[orig_rx]

		return S_new, nlb, nub, rx_mapping

	def get_reaction_activity(self, solution, exp_vector, flux_threshold):
		gimme_fluxes = np.array([kv[0] for i, kv in enumerate(solution.var_values().items())])
		activity = np.zeros(gimme_fluxes.shape)

		activity[(exp_vector > flux_threshold) | (exp_vector == -1)] = 1
		activity[gimme_fluxes > 0] = 2

		return activity