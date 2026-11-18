# Dataset and classes

## Trained classes

The provided model recognizes 38 plant/condition combinations. The exact class
order is defined in `disease_data/class_names.json`. Plant and condition names
use the `Plant___Condition` convention internally, for example:

- `Apple___Apple_scab`
- `Apple___Black_rot`
- `Peach___Bacterial_spot`
- `Strawberry___Leaf_scorch`
- `Tomato___healthy`

Plants outside this reference set, such as rose in the live study test, are
handled by the optional extended identification path rather than by a trained
class.

## Reference library

`disease_data/diseases.json` stores study-facing information for each class:

- `plant`
- `disease`
- `symptoms`
- `severity`
- `recommendedActions`
- `prevention`

A duplicate copy of these files exists at the repository root in the original
working project but is not needed at runtime; the canonical files live in
`disease_data/`.

## Original dataset

The raw training images are not published with this repository because of their
size. The dataset used during training is available from the original project
source:

- [Plant Disease Dataset download](https://drive.usercontent.google.com/download?id=1_5G3Cz0WQtZeTxzsq5lrTUfEnNy78WeY&confirm=t)

You do not need the raw dataset to run the application; the trained model is
included at `model/trained_model.keras`.

## Retraining notes

If you train a replacement model:

1. Export it in Keras `.keras` format.
2. Replace `model/trained_model.keras`.
3. If the class order changes, update `disease_data/class_names.json` and
   `disease_data/diseases.json` together.
4. Re-run `python run.py check` and the smoke tests.

Training and evaluation notebooks are available in [`notebooks/`](../notebooks/).
