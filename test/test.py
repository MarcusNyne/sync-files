import unittest
import os,shutil

from m9lib import uControl, uConfig, uCSV

from m9lib import uLoggerLevel

from _test import *

from c_file_sync import *

class Test_Template(uTestCase):

    test_files = r"test\test_files"
    test_root = r"test\run"
    test_output = r"test\output"

    def __init__(self, methodName = "runTest"):
        super().__init__(methodName)

    def setUp(self):
        self._logger.WriteSubHeader(f"[+BLUE]{self._testMethodName}[+]")
        if os.path.isdir(Test_Template.test_root):
            shutil.rmtree(Test_Template.test_root)
        shutil.copytree(Test_Template.test_files, Test_Template.test_root)
        # print (f"setUp: {self._testMethodName}")
        pass

    def GetFilepath(self, in_filepath):
        root_files = r"test\files"
        if in_filepath is None:
            return root_files
        return os.path.join(root_files, in_filepath)

    def GetTestFolder(self, in_subfolder=None):
        folder = Test_Template.test_root
        if in_subfolder is not None:
            folder = os.path.join(folder, in_subfolder)
        # uFolder.ConfirmFolder(folder)
        return folder
    
    def run_command(self, ini_file):
        uControl.PrintFailures()
        control = uControl("FileSync", os.path.join("test", ini_file))
        control.GetLogger().SetWriteLevel(Level=uLoggerLevel.DETAILS)
        control.GetLogger().SetPrint(Print=True, Level=uLoggerLevel.DETAILS, Color=True)
        control.Execute ()

    def test_review(self):
        self.run_command("test-01-all-files.ini")
        self.check_results("test-01-all-files.csv", {'NEW': 21, 'SAME': 3, 'MOD': 2, 'SKIP': 0, 'REMOVE': 0})

        self.run_command("test-02-exclude.ini")
        self.check_results("test-02-exclude.csv", {'NEW': 1, 'SAME': 0, 'MOD': 0, 'SKIP': 0, 'REMOVE': 0})

        self.run_command("test-03-exclude-nr.ini")
        self.check_results("test-03-exclude-nr.csv", {'NEW': 9, 'SAME': 3, 'MOD': 2, 'SKIP': 0, 'REMOVE': 0})

        self.run_command("test-04-exclude-skip.ini")
        self.check_results("test-04-exclude-skip.csv", {'NEW': 8, 'SAME': 2, 'MOD': 2, 'SKIP': 14, 'REMOVE': 0})

        self.run_command("test-05-exclude-remove.ini")
        self.check_results("test-05-exclude-remove.csv", {'NEW': 7, 'SAME': 2, 'MOD': 2, 'SKIP': 14, 'REMOVE': 3, 'MOVE': 1})

        self.run_command("test-06-exclude-remove.ini")
        self.check_results("test-06-exclude-remove.csv", {'NEW': 6, 'SAME': 2, 'MOD': 2, 'SKIP': 14, 'REMOVE': 2, 'MOVE': 1})

        self.run_command("test-07-exclude-nomove.ini")
        self.check_results("test-07-exclude-nomove.csv", {'NEW': 7, 'SAME': 2, 'MOD': 2, 'SKIP': 14, 'REMOVE': 3, 'MOVE':0})

    def test_rules(self):
        self.run_command("test-10-file-rules.ini")
        self.check_results("test-10-file-rules.csv", {'NEW': 13, 'SAME': 2, 'MOD': 1, 'SKIP': 10, 'REMOVE': 0})

        self.run_command("test-11-file-rules.ini")
        self.check_results("test-11-file-rules.csv", {'NEW': 7, 'SAME': 0, 'MOD': 1, 'SKIP': 18, 'REMOVE': 0})

        self.run_command("test-12-file-rules.ini")
        self.check_results("test-12-file-rules.csv", {'NEW': 2, 'SAME': 0, 'MOD': 0, 'SKIP': 24, 'REMOVE': 0})

        self.run_command("test-13-file-rules.ini")
        self.check_results("test-13-file-rules.csv", {'NEW': 2, 'SAME': 0, 'MOD': 0, 'SKIP': 24, 'REMOVE': 0})

        self.run_command("test-14-file-rules.ini")
        self.check_results("test-14-file-rules.csv", {'NEW': 2, 'SAME': 0, 'MOD': 0, 'SKIP': 24, 'REMOVE': 0})

        self.run_command("test-15-file-rules.ini")
        self.check_results("test-15-file-rules.csv", {'NEW': 7, 'SAME': 1, 'MOD': 1, 'SKIP': 17, 'REMOVE': 0})

        self.run_command("test-16-folder-tags.ini")
        self.check_results("test-16-folder-tags.csv", {'NEW': 19, 'SAME': 2, 'MOD': 2, 'SKIP': 3, 'REMOVE': 0})

        self.run_command("test-17-parent-folder.ini")
        self.check_results("test-17-parent-folder.csv", {'NEW': 2, 'SAME': 2, 'MOD': 2, 'SKIP': 20, 'REMOVE': 0})

    def test_backup(self):
        self.run_command("test-21-backup-review.ini")
        all_files_1 = self.check_files(r'test\run\target')
        self.assertTrue(os.path.isfile(r'test\run\target\images\heart-pillow.jpg'))
        self.assertFalse(os.path.isfile(r'test\run\target\images\items\heart-pillow.jpg'))
        self.check_results("test-21-backup-review.csv", {'NEW': 11, 'SAME': 1, 'MOD': 1, 'SKIP': 13, 'REMOVE': 0, 'MOVE': 0})
        self.run_command("test-22-backup.ini")
        all_files_1 = self.check_files(r'test\run\target')
        self.assertTrue(os.path.isfile(r'test\run\target\images\heart-pillow.jpg'))
        self.assertTrue(os.path.isfile(r'test\run\target\images\items\heart-pillow.jpg'))
        self.check_results("test-22-backup.csv", {'NEW': 11, 'SAME': 1, 'MOD': 1, 'SKIP': 13, 'REMOVE': 0, 'MOVE': 0})
        self.run_command("test-23-backup-repeat.ini")
        all_files_2 = self.check_files(r'test\run\target')
        self.assertTrue(os.path.isfile(r'test\run\target\images\heart-pillow.jpg'))
        self.assertTrue(os.path.isfile(r'test\run\target\images\items\heart-pillow.jpg'))
        self.check_results("test-23-backup-repeat.csv", {'NEW': 0, 'SAME': 13, 'MOD': 0, 'SKIP': 13, 'REMOVE': 0, 'MOVE': 0})
        self.assertEqual(all_files_1, all_files_2)
        self.assertTrue('purple-spiral.PNG' in all_files_1)
        self.assertEqual(len(all_files_1), 22)
        clean_files = self.check_files(r'test\run\target\_clean')
        self.assertEqual(len(clean_files), 3)
        self.assertTrue('horns.jpg' in clean_files)
        pass

    def test_sync(self):
        self.run_command("test-25-sync-review.ini")
        all_files_5 = self.check_files(r'test\run\target')
        self.assertTrue(os.path.isfile(r'test\run\target\images\heart-pillow.jpg'))
        self.assertFalse(os.path.isfile(r'test\run\target\images\items\heart-pillow.jpg'))
        self.assertTrue(os.path.isfile(r'test\run\target\_clean\purple.doc'))
        self.assertFalse(os.path.isfile(r'test\run\target\images\purple.doc'))
        self.check_results("test-25-sync-review.csv", {'NEW': 9, 'SAME': 1, 'MOD': 1, 'SKIP': 13, 'REMOVE': 5, 'MOVE': 2})
        self.run_command("test-26-sync.ini")
        all_files_6 = self.check_files(r'test\run\target')
        self.assertFalse(os.path.isfile(r'test\run\target\images\heart-pillow.jpg'))
        self.assertTrue(os.path.isfile(r'test\run\target\images\items\heart-pillow.jpg'))
        self.assertFalse(os.path.isfile(r'test\run\target\_clean\purple.doc'))
        self.assertTrue(os.path.isfile(r'test\run\target\images\purple.doc'))
        self.check_results("test-26-sync.csv", {'NEW': 9, 'SAME': 1, 'MOD': 1, 'SKIP': 13, 'REMOVE': 5, 'MOVE': 2})
        self.run_command("test-27-sync-repeat.ini")
        all_files_7 = self.check_files(r'test\run\target')
        self.assertFalse(os.path.isfile(r'test\run\target\images\heart-pillow.jpg'))
        self.assertTrue(os.path.isfile(r'test\run\target\images\items\heart-pillow.jpg'))
        self.assertFalse(os.path.isfile(r'test\run\target\_clean\purple.doc'))
        self.assertTrue(os.path.isfile(r'test\run\target\images\purple.doc'))
        self.check_results("test-27-sync-repeat.csv", {'NEW': 0, 'SAME': 13, 'MOD': 0, 'SKIP': 13, 'REMOVE': 0, 'MOVE': 0})
        self.assertEqual(len(all_files_5), 10)
        self.assertEqual(all_files_6, all_files_7)
        self.assertTrue('purple-spiral.PNG' in all_files_6)
        self.assertEqual(len(all_files_6), 20)
        clean_files = self.check_files(r'test\run\target\_clean')
        self.assertEqual(len(clean_files), 7)
        self.assertTrue('horns.jpg' in clean_files)
        self.assertTrue('black_cat.jpg' in clean_files)
        self.assertTrue('black_cat-001.jpg' in clean_files)
        pass

    def check_results(self, filename, expected):
        csv = uCSV()
        csv.ReadFile(os.path.join(self.test_output, filename))
        rows = csv.GetRows()
        all_stats = ['NEW', 'SAME', 'MOD', 'SKIP', 'REMOVE', 'MOVE']
        results = {}
        for stat in all_stats:
            results[stat] = 0
        for row in rows:
            if row[3] in results:
                results[row[3]] += 1
        for stat in all_stats:
            if stat in expected:
                self.assertEqual(expected[stat], results[stat], stat)
        pass

    def check_files(self, filepath, recurse=True):
        return [f[0] for f in uFolder.FindFiles(filepath, Recurse=recurse)]

if os.path.isdir(Test_Template.test_output):
    shutil.rmtree(Test_Template.test_output)
os.mkdir(Test_Template.test_output)

try:
    unittest.main(verbosity=0)
except:
    pass

uTestCase.WriteSummary()
