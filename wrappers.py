"""
wrappers.py
-----------
Tool wrappers that sit between calling code and hardware functions.

The pattern:
  Calling code passes a pin NAME (string like "red").
  The wrapper resolves that name to the actual pyfirmata pin object
  stored in context.pins, then calls the real function.

Why this layer exists:
  - Calling code stays readable — it speaks in names, not objects.
  - Hardware can be swapped without touching the calling code.
  - In simulation mode, fake pins are stored in context.pins,
    so the same calling code works without any real hardware.

Two wrappers are provided:
  tool_wrapper          -- resolves args from context.vars
  hardware_tool_wrapper -- resolves pin names from context.pins
"""

from typing import Callable, Any
from context import SystemContext


def tool_wrapper(fn: Callable) -> Callable:
    """
    Basic context variable resolver.

    Before calling fn, checks each argument value.
    If the value is a string that exists as a key in context.vars,
    it is replaced with the actual stored value.

    Example:
        context.set("TARGET_PIN", some_pin_object)
        wrapped_fn(context, pin="TARGET_PIN")
        # fn receives: pin=some_pin_object
    """
    def wrapped(context: SystemContext, **args) -> Any:
        resolved = {}
        for k, v in args.items():
            if isinstance(v, str) and v in context.vars:
                resolved[k] = context.get(v)
            else:
                resolved[k] = v
        return fn(context=context, **resolved)
    return wrapped


def hardware_tool_wrapper(fn: Callable, pin_keys: tuple = ("pin",)) -> Callable:
    """
    Hardware pin resolver.

    Before calling fn, checks each argument whose key is listed in pin_keys.
    If the value is a string that exists in context.pins,
    it is replaced with the actual pyfirmata pin object.

    Falls back to context.vars resolution for non-pin arguments.

    Why separate from tool_wrapper?
      Pins live in context.pins. Logic data lives in context.vars.
      They are separate stores for a reason — mixing them would make
      the context harder to inspect and debug.

    Example:
        hardware_tool_wrapper(_set_led, pin_keys=("pin",))
        set_led(context, pin="red", state=True)
        # fn receives: pin=<pyfirmata Pin object for pin 2>
    """
    def wrapped(context: SystemContext, **args) -> Any:
        resolved = {}
        for k, v in args.items():
            if k in pin_keys and isinstance(v, str) and v in context.pins:
                resolved[k] = context.pins[v]
            elif isinstance(v, str) and v in context.vars:
                resolved[k] = context.get(v)
            else:
                resolved[k] = v
        return fn(context=context, **resolved)
    return wrapped
