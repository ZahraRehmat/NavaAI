import unittest
from smart_labels import smart_label,PREFERRED,ALPHABET
from smart_grid import SmartMap
from test_smart_grid import row
from command_voice import CommandVoice


class SmartLabelTests(unittest.TestCase):
    def test_confusable_letters_deferred_until_clear_singles_exhausted(self):
        first=[smart_label(i) for i in range(len(PREFERRED))]
        self.assertEqual(first,list(PREFERRED))
        for group in ('BCDEGPTVZ','AJK','FSX','MN','GJ'):
            self.assertLessEqual(len(set(first)&set(group)),1)
        self.assertEqual(set(smart_label(i) for i in range(26)),set('ABCDEFGHIJKLMNOPQRSTUVWXYZ'))

    def test_labels_unique_across_single_pair_and_triple_boundaries(self):
        labels=[smart_label(i) for i in range(5000)]
        self.assertEqual(len(set(labels)),len(labels))
        self.assertEqual(labels[26],'AA');self.assertEqual(labels[27],'AF')
        self.assertTrue(all(len(label)==1 for label in labels[:26]))
        self.assertEqual(len(labels[702]),3)

    def test_refresh_keeps_identity_and_never_reuses_a_removed_label(self):
        grid=SmartMap([(0,0,800,600)])
        grid.update([row(str(i)) for i in range(30)])
        original={key:label for key,label in grid.labels.items()}
        grid.update([row(str(i)) for i in reversed(range(30))])
        self.assertEqual(grid.labels,original)
        grid.update([row('new')])
        self.assertNotIn(next(iter(grid.targets)),original.values())

    def test_voice_routes_new_alphabet_and_nato_labels(self):
        labels=[smart_label(i) for i in range(80)]
        context={'grid_active':True,'labels':labels}
        session=CommandVoice({'handsfree':True})
        for spoken,wanted in (('eff','F'),('click alpha foxtrot','click AF')):
            result=session.route({'text':spoken,'confidence':1},context)
            self.assertEqual(result['kind'],'command');self.assertEqual(result['text'],wanted)


if __name__=='__main__':unittest.main()
