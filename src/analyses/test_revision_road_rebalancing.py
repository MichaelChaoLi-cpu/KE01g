"""Small independent edge cases for the ROAD sensitivity implementation."""
import unittest
import numpy as np
import pandas as pd
from compare_revision_road_rebalancing import shortest, allocate, construct_screen


class RoadTests(unittest.TestCase):
    def test_parallel_edges_and_disconnected_node(self):
        graph = [[(1,10,0),(1,2,1)],[(0,10,0),(0,2,1),(2,3,2)],[(1,3,2)],[]]
        d,p = shortest(graph,0,{0,1,2,3})
        self.assertEqual(d[2],5)
        self.assertEqual(p[1],(0,1))
        self.assertNotIn(3,d)

    def test_partial_edge_and_identical_projection(self):
        # One 100-m source edge split at 20 m and 60 m.
        graph = [[(2,20,0)],[(3,40,2)],[(0,20,0),(3,40,1)],[(2,40,1),(1,40,2)]]
        d,_ = shortest(graph,2,{2,3})
        self.assertEqual(d[2],0)
        self.assertEqual(d[3],40)

    def test_donor_tie_break_and_unreachable_recipient(self):
        frame = pd.DataFrame({
            'Shelter Number':[2,1,3], 'Evacuees':[0,0,40],
            'Temporary Toilets Installed':[1,1,0], 'Toilet Cars':[0,0,0],
            'Water Status':['〇','〇','×'],
            'Estimated Functional Support Evacuees':[0,0,4],
            'Estimated Female Functional Support Evacuees':[0,0,2]})
        screen = construct_screen(frame)
        dist = np.array([[0.,1.,2.],[1.,0.,2.],[2.,2.,0.]])
        flows,metrics = allocate(screen,'full',dist)
        self.assertEqual(flows,[(1,2,1),(0,2,1)])
        self.assertEqual(metrics['Residual Screening Shortfall'],0)
        dist[:2,2] = np.inf
        flows,metrics = allocate(screen,'full',dist)
        self.assertEqual(flows,[])
        self.assertEqual(metrics['Residual Screening Shortfall'],2)


if __name__ == '__main__':
    unittest.main()
