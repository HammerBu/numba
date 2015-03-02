"""
Contains function decorators and target_registry
"""
from __future__ import print_function, division, absolute_import
import warnings
from . import sigutils
from .targets import registry

# -----------------------------------------------------------------------------
# Decorators


def autojit(*args, **kws):
    """Deprecated.

    Use jit instead.  Calls to jit internally.
    """
    warnings.warn("autojit is deprecated, use jit instead which now performs "
                  "the same functionality", DeprecationWarning)
    return jit(*args, **kws)


def jit(signature_or_function=None, locals={}, target='cpu', **options):
    """
    This decorator is used to compile a Python function into native code.
    
    Args
    -----
    signature:
        The (optional) signature or list of signatures to be compiled.
        If not passed, required signatures will be compiled when the
        decorated function is called, depending on the argument values.
        As a convenience, you can directly pass the function to be compiled
        instead.

    locals: dict
        Mapping of local variable names to Numba types. Used to override the
        types deduced by Numba's type inference engine.

    targets: str
        Specifies the target platform to compile for. Valid targets are cpu,
        gpu, npyufunc, and cuda. Defaults to cpu.

    targetoptions: 
        For a cpu target, valid options are:
            nopython: bool
                Set to True to disable the use of PyObjects and Python API
                calls. The default behavior is to allow the use of PyObjects
                and Python API. Default value is False.

            forceobj: bool
                Set to True to force the use of PyObjects for every value.
                Default value is False.

            looplift: bool
                Set to True to enable jitting loops in nopython mode while
                leaving surrounding code in object mode. This allows functions
                to allocate NumPy arrays and use Python objects, while the
                tight loops in the function can still be compiled in nopython
                mode. Any arrays that the tight loop uses should be created
                before the loop is entered. Default value is True.

            wraparound: bool
                Set to True to enable array indexing wraparound for negative
                indices, for a small performance penalty. Default value
                is True.

    Returns
    --------
    A callable usable as a compiled function.  Actual compiling will be
    done lazily if no explicit signatures are passed.

    Examples
    --------
    The function can be used in the following ways:

    1) jit(signatures, target='cpu', **targetoptions) -> jit(function)

        Equivalent to:

            d = dispatcher(function, targetoptions)
            for signature in signatures:
                d.compile(signature)

        Create a dispatcher object for a python function.  Then, compile
        the function with the given signature(s).

        Example:

            @jit("int32(int32, int32)")
            def foo(x, y):
                return x + y

            @jit(["int32(int32, int32)", "float32(float32, float32)"])
            def bar(x, y):
                return x + y

    2) jit(function, target='cpu', **targetoptions) -> dispatcher

        Create a dispatcher function object that specializes at call site.

        Examples:

            @jit
            def foo(x, y):
                return x + y

            @jit(target='cpu', nopython=True)
            def bar(x, y):
                return x + y

    """

    # Handle signature
    if signature_or_function is None:
        # No signature, no function
        def configured_jit(func):
            return jit(func, locals=locals, target=target, **options)
        return configured_jit
    elif isinstance(signature_or_function, list):
        # A list of signatures is passed
        return _jit(signature_or_function, locals=locals, target=target,
                    targetoptions=options)
    elif sigutils.is_signature(signature_or_function):
        # A single signature is passed
        return _jit([signature_or_function], locals=locals, target=target,
                    targetoptions=options)
    else:
        # A function is passed
        pyfunc = signature_or_function
        dispatcher = registry.target_registry[target]
        dispatcher = dispatcher(py_func=pyfunc, locals=locals,
                                targetoptions=options)
        return dispatcher


def _jit(sigs, locals, target, targetoptions):
    dispatcher = registry.target_registry[target]

    def wrapper(func):
        disp = dispatcher(py_func=func, locals=locals,
                          targetoptions=targetoptions)
        for sig in sigs:
            disp.compile(sig)
        disp.disable_compile()
        return disp

    return wrapper


def njit(*args, **kws):
    """
    Equivalent to jit(nopython=True)

    See documentation for jit function/decorator for full description.
    """
    if 'nopython' in kws:
        warnings.warn('nopython is set for njit and is ignored', RuntimeWarning)
    if 'forceobj' in kws:
        warnings.warn('forceobj is set for njit and is ignored', RuntimeWarning)
    kws.update({'nopython': True})
    return jit(*args, **kws)


