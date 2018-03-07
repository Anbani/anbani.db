# Overview

This repo contains various datasets in Georgian for NLP or other purposes. These are entire text of "The Knight with the Panther skin" `vefxistyaosani.txt`, Georgian aphorisms `aforizmebi.txt`, first and last names of Georgian poets and writers `poetswriters.txt`, baby names in Georgian `names.csv` (© kids.ge), and full Georgian Alphabet `anbani.csv` with corresponding descriptions of the letters as it appears in Unicode. 

Some of these datasets were fed to Neural Networks (char-rnn by Andrej Karpathy) to generate fake data, such as `fake-aforizmebi.txt`, `fake-names.txt` trained on Georgian (origin) subset, `fake-poetswriters.txt`.


## Datasets

| Name               | Description                                             | Source                | Count      | URL |
|--------------------|---------------------------------------------------------|-----------------------|------------|-----|
| vefxistyaosani.txt | Entire text of "The Knight with the Panther skin"       | don't remember        | 8524 lines | [Download](https://github.com/Anbani/anbani.db/blob/master/datasets/vefxistyaosani.txt)
| aforizmebi.txt     | Georgian aphorisms                                      | various sources       | 132 lines  | [Download](https://github.com/Anbani/anbani.db/blob/master/datasets/aforizmebi.txt)
| poetswriters.txt   | First and Last names of Georgian Poets and Writers      | ka.wikipedia.org      | 544 lines  | [Download](https://github.com/Anbani/anbani.db/blob/master/datasets/poetswriters.txt)
| names.csv          | Baby names in Georgian with various origins             | kids.ge ©             | 2094 lines | [Download](https://github.com/Anbani/anbani.db/blob/master/datasets/names.csv)
| anbani.csv         | Full Georgian alphabet with descriptions and char codes | unicode.org           | 175 lines  | [Download](https://github.com/Anbani/anbani.db/blob/master/datasets/anbani.csv)


## Fakesets

| Name                  | Description                                             | Source          | Count       | URL |
|-----------------------|---------------------------------------------------------|-----------------|-------------|-----|
| fake-aforizmebi.txt   | Georgian aphorisms generated using char-rnn             | anbani.db       | 17047 lines | [Download](https://github.com/Anbani/anbani.db/blob/master/fakesets/fake-aforizmebi.txt)
| fake-poetswriters.txt | Fake poetic names trained on Georgian poets and writers | anbani.db       | 2514 lines  | [Download](https://github.com/Anbani/anbani.db/blob/master/fakesets/fake-poetswriters.txt)
| fake-names.csv        | Fake names trained on Georgian subset of baby names     | anbani.db       | 60961 lines | [Download](https://github.com/Anbani/anbani.db/blob/master/fakesets/fake-names.csv)


# Resources
Fake Georgian text and names generation is supported by `anbani.js` - a multifunctional Javascript library for working with Georgian Alphabet. Read more about the package here [[anbani/anbani.js]](https://github.com/Anbani/anbani.js)
```bash
npm install anbani
```
```javascript
var anbani = require('anbani')

anbani.core.convert("ანბანი", "მხედრული", "ასომთავრული")
// 'ႠႬႡႠႬႨ'

anbani.lorem.names(3)
// ['დამერ გაშვითელი', 'სიბო ყორთელია', 'გიმოლ ვაწოშვილი']

anbani.lorem.sentences(10)
// 'მოეხვიდეს სიტირენ გიშიხარნი. წეითო გამიზრიან, ჰქონთავისთან გემრუფენ, უკრთებოდემნი მესმანცა მყივნე.'
```


# Disclaimer
Datasets are available freely for non-commercial purposes only. For commercial purposes, contact the corresponding source. 

