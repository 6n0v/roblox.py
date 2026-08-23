arawe
======

A lightweight Python wrapper for the Roblox API focused on user data and economy.

Key Features
-------------

- Modern Pythonic API using ``async`` and ``await``.
- Purchase and revoke gamepasses.
- Retrieve Roblox user data (with limitations).

Installing
-----------

**Python 3.8 or higher is required**

To install the library, you can just run the following command:

.. note::

    A `Virtual Environment <https://docs.python.org/3/library/venv.html>`__ is recommended to install
    the library, especially on Linux where the system Python is externally managed and restricts which
    packages you can install on it.

.. code:: sh

    # Linux/macOS
    python3 -m pip install arawe

    # Windows
    py -3 -m pip install arawe

Quick Example
--------------

.. code:: py

    import asyncio

    import roblox

    async def main():
        async with roblox.Roblox() as client:
            await client.get_user(1)

    asyncio.run(main())

You can find more examples in the examples directory.

Links
------

- `Roblox <https://roblox.com/>`_
- `discord.py <https://github.com/rapptz/discord.py>`_
- `ro.py <https://github.com/ro-py/ro.py>`_
