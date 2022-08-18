# py2math - convert Python objects to Latex math

With py2math you can convert some python object `x` to a Latex math string by simply calling `py2math(x)`. The result is automatically displayed as math in Jupyter notebooks.

## Setup

Install the requirements ([lark](https://github.com/lark-parser/lark)), e.g. by
```sh
pip install -r requirements.txt
```
then import py2math with
```python
from py2math import py2math
```
assuming the `py2math.py` file is in the same folder.

A pip-package might be provided at a later point in time.


## Example

```python
from py2math import py2math

def f(x):
    return x**2 / (x + 2)

py2math(f)
```
results in:

$$ f(x) = \frac{{x}^{2}}{x+2} $$

```latex
f(x) = \frac{{x}^{2}}{x+2}
```
