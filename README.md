# Overview

This repo contains various datasets in Georgian for NLP or other purposes. These are entire text of "The Knight with the Panther skin" `vefxistyaosani.txt`, Georgian aphorisms `aforizmebi.txt`, first and last names of Georgian poets and writers `poetswriters.txt`, baby names in Georgian `names.csv` (© kids.ge), and full Georgian Alphabet `anbani.csv` with corresponding descriptions of the letters as it appears in Unicode. 

Some of these datasets were fed to Neural Networks (char-rnn by Andrej Karpathy) to generate fake data, such as `fake-aforizmebi.txt`, `fake-names.txt` trained on Georgian (origin) subset, `fake-poetswriters.txt`.


## Datasets
Here's a detailed table for the datasets:
| Name               | Description                                             | Source                | Count      |
|--------------------|---------------------------------------------------------|-----------------------|------------|
| vefxistyaosani.txt | Entire text of "The Knight with the Panther skin"       | don't remember        | 8524 lines |
| aforizmebi.txt     | Georgian aphorisms                                      | various sources       | 132 lines  |
| poetswriters.txt   | First and Last names of Georgian Poets and Writers      | ka.wikipedia.org      | 544 lines  |
| names.csv          | Baby names in Georgian with various origins             | kids.ge © | 2094 lines |
| anbani.csv         | Full Georgian alphabet with descriptions and char codes | unicode.org           | 175 lines  |


## Fakesets
Here's a detailed table for the fakesets:
| Name                  | Description                                             | Source          | Count       |
|-----------------------|---------------------------------------------------------|-----------------|-------------|
| fake-aforizmebi.txt   | Georgian aphorisms generated using char-rnn             | anbani.db | 17047 lines |
| fake-poetswriters.txt | Fake poetic names trained on Georgian poets and writers | anbani.db | 2514 lines  |
| fake-names.csv        | Fake names trained on Georgian subset of baby names     | anbani.db | 60961 lines |


# Resources
Fake Georgian text and names generation is supported by `anbani.js` - a multifunctional Javascript library for working with Georgian Alphabet. 