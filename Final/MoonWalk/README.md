# MoonWalk
Story navigation via textual input
![Main](figures/main.png)

## Setup
This project includes a custom inference backend that is not being deployed. To run locally,

**Step 1**: Install the environment
```
pip install -r requirements.txt
```

**Step 2**: Download the checkpoint
This project is using the [UniVTG model](https://github.com/showlab/UniVTG). Download [this](https://drive.google.com/drive/folders/1-eGata6ZPV0A1BBsZpYyIooos9yjMx2f) checkpoint, unzip it, and put the ```opt.json``` and the ```.ckpt``` file in ```MoonWalk\univtg\ckpts```.


**Step 3**: Run the project \
Navigate to the ```Moonwalk``` directory. Run the backend by running
```
python -m back.back
```
Then open ```front/index.html```
