# MoonWalk
Moonwalk is an interactive storytelling experience that allow users to navigate a story via textual input
![Main](figures/main.png)

# Motivation
There are two main properties of neural networks that may be conducive to interactive storytelling. First, neural networks model a distribution of information, and the actual contents are sampled from the distribution. For example, LLM nad generate different ways to express thankfulness, such as thank you, thanks, and I'm grateful. The actual contents are different, but their underlying meanings are the same. This may enable interactive storytelling to be more individualized and move away from the rigid multiple choice paradigm. The model is capable of generating different content, or digest different user inputs, while still maintaining a multiple choice structure. Secondly, neural networks are capable of capturing the abstracted information, which humans can make connections in a more implicit way. This will allow audiences to be in a more flow-like state when engaging in these experiences, without needing to face explicit choices.


Moonwalk, as a prototype for my thesis project, interprets interactive storytelling as a space of clips with a loop. The user will input text, and the algorithm will map the text to what is being pre recorded in my footages. The different possibilities of footages and the way to assemble them create a space of video that audiences can observe, and the process of inputting text is thus the process of navigating this space, and gain one's own perspective on the story.


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
