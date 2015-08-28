import traceback
import cProfile
import pstats
import hashlib
from cStringIO import StringIO
from utils import indent, magic_timeit, magic_memit, getTable


class Benchmark(object):
    def __init__(self, code, setup, ncalls=None, repeat=3, cleanup=None,
       name=None, description=None, logy=False, db_path=None):
        self.code = code
        self.setup = setup
        self.cleanup = cleanup or ''
        self.ncalls = ncalls
        self.repeat = repeat

        self.name = name
        self.description = description
        self.logy = logy
        self.db_path = db_path

    def __repr__(self):
        return "Benchmark('%s')" % self.name

    def _setup(self):
        ns = globals().copy()
        exec(self.setup in ns)
        return ns

    @property
    def checksum(self):
        return hashlib.md5(self.setup + self.code + self.cleanup).hexdigest()

    def _cleanup(self, ns):
        exec(self.cleanup in ns)

    def to_rst(self, results):
        output = """**Benchmark setup**

.. code-block:: python

%s

**Benchmark statement**

.. code-block:: python

%s

%s
""" % (indent(self.setup), indent(self.code),
        getTable(results['runtime'], self.name,
                ['name', 'repeat', 'timing', 'loops', 'units']))

        return output

    def profile(self, ncalls):
        prof = cProfile.Profile()
        ns = self._setup()

        code = compile(self.code, '<f>', 'exec')

        def f(*args, **kwargs):
            for i in xrange(ncalls):
                exec(code in ns)

        prof.runcall(f)

        return pstats.Stats(prof).sort_stats('cumulative')

    def run(self):
        results = {}
        results['memory'] = self.run_memit()
        results['runtime'] = self.run_timeit()

        return results

    def run_timeit(self):
        ns = self._setup()

        try:
            result = magic_timeit(ns, self.code, ncalls=self.ncalls,
                repeat=self.repeat, force_ms=True)

            result['success'] = True

        except:
            buf = StringIO()
            traceback.print_exc(file=buf)
            result = {'success': False, 'traceback': buf.getvalue()}

        self._cleanup(ns)
        return result

    def run_memit(self):
        ns = self._setup()

        try:
            result = magic_memit(ns, self.code, ncalls=self.ncalls,
                repeat=self.repeat)

            result['success'] = True

        except:
            buf = StringIO()
            traceback.print_exc(file=buf)
            result = {'success': False, 'traceback': buf.getvalue()}

        self._cleanup(ns)
        return result


class BenchmarkSuite(list):
    """Basically a list, but the special type is needed for discovery"""
    @property
    def benchmarks(self):
        """Discard non-benchmark elements of the list"""
        return filter(lambda elem: isinstance(elem, Benchmark), self)


def gather_benchmarks(ns):
    benchmarks = []
    for v in ns.values():
        if isinstance(v, Benchmark):
            benchmarks.append(v)
        elif isinstance(v, BenchmarkSuite):
            benchmarks.extend(v.benchmarks)
    return benchmarks
