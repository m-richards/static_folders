# Static Folders
The premise for this library is simple: you want a statically typed way to refer to a catalogue of data.

## Why would you want this?
Let's start with some alternatives I've seen to managing this problem this:
```python
from Pathlib import Path
data_dir = Path("d:/projects/<project>/data") # person A
# data_dir = Path("/mnt/data/projects/<project>/data") # person B
config = data_dir / "config.json"
regression_inputs_csv = data_dir / "regression_model"/"input.csv"
```
There are a few pain points here:
1. Code you need to swap out depending on which machine things are being run on, which often tends to end up across 
multiple notebooks (this is not something this library solves, but having a reusable folder structure encourages one
to thing about having a more centralised mechanism to manage these kinds of things, rather that commented code in scripts)
2. You can end up with a lot of variables quickly if you have lots of files
3. If you want to compose pieces with constants you end up with even more variables
4. No autocompletion from an editor
5. If you ever need to move a file you're reliant on find+replace / regex to make sure you update all the usages (
   which becomes more error-prone as you try to reuse path pieces, as the there are more text replacement variants
   )

A solution to this is some kind of wrapper class:

```python
@define
class ApplicationPaths:
    root: Path
    
    def get_config(self)->Path:
       ...
```
This works fine, but you get no structure around the internals, only an external API which is statically typed. The 
same issues persist around changing your data representation, and if you want to specify
detail within a nested subpath, you end up with a lot of methods, which can become unwieldly.

Static Folders provides a type-checked interface to represent a folder tree:

```python
from pathlib import Path
from static_folders import Folder

class RegressionModelData(Folder):
    input_csv: Path = Path("input.csv")
  

class ApplicationData(Folder):
    regression_model_data: RegressionModelData = RegressionModelData("regression_model_data")
    config: Path = Path("config.json")

app_root = ApplicationData("d:/projects/<project>/data")
print(app_root.regression_model_data.input_csv.read_text())
```
We also provide some convenience inference based on type annotations, to reduce the amount of boilerplate being
written - we could equivalently write the above class as:
```python
class ApplicationData(Folder):
    regression_model_data: RegressionModelData
    config: Path = Path("config.json")
```
for the same result.




## Why are you hard coding file paths, shouldn't your code be more modular?
Sometimes it's quite useful to be able to explicitly refer to a catalog of data inputs e.g.
- Data science / analytics or processing pipelines
- GIS data transformations
- For complicated applications with quite specific input requirements e.g. transport models

That doesn't mean you should write your code coupled to Folder instances, you can (and probably should) still seperate
business logic from data representation. There's a similar concept well explained in the [cattrs](https://catt.rs/en/stable/why.html) 
documentation - that the serialisation of your data model should be a decoupled concern from the data model itself. In the same way,
_static folders_ deals with the data representation of your inputs, which should be seperate from how your
code actually processes data.


## But what if I have data on the cloud / stored in some way that doesn't fit this model?
- If your data is sufficiently small, you might be able to mirror the data (this can be quite useful working
in a transport modelling ecosystem where inspecting and checking input and output files independently of
code can be very valuable, and having an explicit mirror makes things easy to find)
- If not, or you're intrinsically coupled to cloud storage, then _static folders_ probably isn't a good fit.
