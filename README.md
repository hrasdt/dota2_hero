dota2_hero
==========

A Python module to read the list of heroes in Dota 2 from Valve's website. Does not require an API key.

Run the python file with "--help" for usage as a script, or run `pydoc dota2_hero` in the directory for module documentation.
The source is only 300 lines, so you can always read that as a guide.

To get started, try:
```python
for h in dota2_hero.get_all_heroes():
    print(h)
```
Note that `get_all_heroes()` returns a generator.
