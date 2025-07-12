import os
import unittest
import shutil

from m9lib import uFileLogger, uLoggerLevel
from m9lib import uFolder

import inspect

class uTestCase(unittest.TestCase):
    _logger = None
    _summary = {'_tests':[]}

    def __init__(self, methodName = "runTest"):
        super().__init__(methodName)

        if uTestCase._logger is None:
            uTestCase._logger = uFileLogger(r"test\logs\{YMD}-{TSM}-Test Results.log")
            uTestCase._logger.SetWriteLevel(Level=uLoggerLevel.DETAILS)
            uTestCase._logger.SetPrint(Print=True, Level=uLoggerLevel.DETAILS, Color=True)
            uTestCase._logger.WriteHeader("[+BLUE]Unit Test Results[+]")
            uFolder.TrimOldFiles(r"test\logs", "*.log", KeepCount=3)

    def __test_method(self, in_depth=2):
            stack = inspect.stack()
            if stack[in_depth+1].function=="check_results":
                in_depth += 1
            for s in stack:
                 if s.function.startswith("test_"):
                      return {"test_func": s.function, "assert_func": stack[in_depth].function, "assert_file": stack[in_depth+1].filename, "assert_line": stack[in_depth+1].lineno}

            return None
    
    def __count_assert(self, in_test, in_success):
        if in_test not in uTestCase._summary:
            uTestCase._summary['_tests'].append(in_test)
            uTestCase._summary[in_test] = (0,0)

        if in_success:
            uTestCase._summary[in_test] = (uTestCase._summary[in_test][0]+1, uTestCase._summary[in_test][1])
        else:
            uTestCase._summary[in_test] = (uTestCase._summary[in_test][0], uTestCase._summary[in_test][1]+1)

    def __count_success(self):
        method = self.__test_method()
        if method is not None:
            self.__count_assert(method['test_func'], True)
    
    def __log_failure(self, c1=None, c2=None, msg=None):
        method = self.__test_method()
        if method is None:
             uTestCase._logger.WriteError("Unknown exception")
             return
        
        self.__count_assert(method['test_func'], False)
             
        post = ""
        if c2 is not None:
            post = f": ({c1}, {c2})"
        elif c1 is not None:
            post = f": ({c1})"

        message = f"[{method['test_func']}] {method['assert_func']}{post} | {os.path.basename(method['assert_file'])} ({method['assert_line']})"
        if msg is not None:
             message += f" | {msg}"

        uTestCase._logger.WriteError(message)

    @classmethod
    def WriteSummary(cls):
        if uTestCase._logger:
            uTestCase._logger.WriteSubHeader("[+BLUE]Summary[+]")
            cnt_tests = 0
            cnt_failures = 0
            for test in uTestCase._summary['_tests']:
                if test.startswith('test_'):
                    summary = uTestCase._summary[test]
                    test_result = f"[+CYAN]{test} ([+][+BLUE]{summary[0]+summary[1]}[+][+CYAN])[+]"
                    cnt_tests += summary[0]+summary[1]
                    if summary[1]>0:
                        uTestCase._logger.WriteWarning(test_result + f": [+RED]{summary[1]} failures[+]")
                        cnt_failures += summary[1]
                    else:
                        uTestCase._logger.WriteLine(test_result)

            uTestCase._logger.WriteSubDivider()

            if cnt_failures>0:
                uTestCase._logger.WriteLine(f"{cnt_tests} tests ({cnt_failures} failures)")
            else:
                uTestCase._logger.WriteLine(f"{cnt_tests} tests (all successful)")

    def assertFalse(self, expr, msg=None):
        """Check that the expression is false."""
        try:
            unittest.TestCase.assertTrue(self, expr is not True, msg)
            self.__count_success()
        except Exception as e:
            self.__log_failure(expr, msg=msg)
            # raise e

    def assertTrue(self, expr, msg=None):
        """Check that the expression is true."""
        try:
            unittest.TestCase.assertTrue(self, expr is True, msg)
            self.__count_success()
        except Exception as e:
            self.__log_failure(expr, msg=msg)
            # raise e

    def assertEqual(self, first, second, msg=None):
        """Fail if the two objects are unequal as determined by the '=='
           operator.
        """
        try:
            unittest.TestCase.assertEqual(self, first, second, msg)
            self.__count_success()
        except Exception as e:
            self.__log_failure(first, second, msg)
            # raise e

    def assertNotEqual(self, first, second, msg=None):
        """Fail if the two objects are equal as determined by the '!='
           operator.
        """
        try:
            unittest.TestCase.assertNotEqual(self, first, second, msg)
            self.__count_success()
        except Exception as e:
            self.__log_failure(first, second, msg=msg)
            # raise e

    def assertFolderExists(self, filepath, msg=None):
        try:
            unittest.TestCase.assertTrue(self, os.path.isdir(filepath), msg)
            self.__count_success()
        except Exception as e:
            self.__log_failure(filepath, msg=msg)
            # raise e

    def assertFileExists(self, filepath, msg=None):
        try:
            unittest.TestCase.assertTrue(self, os.path.isfile(filepath), msg)
            self.__count_success()
        except Exception as e:
            self.__log_failure(filepath, msg=msg)
            # raise e
