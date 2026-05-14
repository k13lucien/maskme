How to Create a Custom Strategy
===============================

MaskMe is designed to be extensible. You can add your own anonymization logic by following these steps.

1. Create a Strategy Function
-----------------------------

A strategy is a simple function that takes a value and returns a transformed one.

.. code-block:: python

   def my_custom_strategy(value, **kwargs):
       return f"custom-{value}"

2. Register the Strategy
------------------------

Add your function to the strategy registry in ``src/maskme/strategies/__init__.py``.

.. code-block:: python

   from .my_module import my_custom_strategy

   STRATEGIES = {
       # ...
       "my_custom": my_custom_strategy,
   }

3. Use it in your Rules
-----------------------

.. code-block:: json

   {
     "field": "my_custom"
   }
