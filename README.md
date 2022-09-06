# mensahd
Parsers for openmensa.org. The parsers runs in a [Github action](https://github.com/cvzi/mensahd/actions?query=workflow%3ARunParsers) and push the XML feeds to [Github pages](https://cvzi.github.io/mensahd/)



[![Test xml meta and feeds](https://github.com/cvzi/mensahd/workflows/Test%20xml%20meta%20and%20feeds/badge.svg)](https://github.com/cvzi/mensahd/actions?query=workflow%3A%22Test+xml+meta+and+feeds%22)
[![Codacy Badge](https://api.codacy.com/project/badge/Grade/e2aa5ab1cb304c0ab1f5719ad2b3acbf)](https://app.codacy.com/app/cvzi/mensahd?utm_source=github.com&utm_medium=referral&utm_content=cvzi/mensahd&utm_campaign=Badge_Grade_Dashboard)

Parser for [openmensa.org](https://openmensa.org/) for canteens of
[Studierendenwerk Heidelberg](http://www.stw.uni-heidelberg.de/en/speiseplan),
[Studierendenwerk Mannheim](https://www.stw-ma.de/Essen+_+Trinken/Men%C3%BCpl%C3%A4ne.html),
[Studierendenwerk Stuttgart](https://www.studierendenwerk-stuttgart.de/gastronomie/speiseangebot)
and [Studierendenwerk Ulm](https://studierendenwerk-ulm.de/essen-trinken/speiseplaene/).

Parser für [openmensa.org](https://openmensa.org/) für die Mensen des
[Studierendenwerk Heidelberg](http://www.stw.uni-heidelberg.de/de/speiseplan),
[Studierendenwerk Mannheim](https://www.stw-ma.de/Essen+_+Trinken/Men%C3%BCpl%C3%A4ne.html),
[Studierendenwerk Stuttgart](https://www.studierendenwerk-stuttgart.de/gastronomie/speiseangebot)
und [Studierendenwerk Ulm](https://studierendenwerk-ulm.de/essen-trinken/speiseplaene/).

|  Feeds       |                                         Status                                                                                                                  |                     Cron                                                                                                                                      |
|:------------:|:---------------------------------------------------------------------------------------------------------------------------------------------------------------:|:-------------------------------------------------------------------------------------------------------------------------------------------------------------:|
| today        | [![RunParsersToday](https://github.com/cvzi/mensahd/workflows/RunParsersToday/badge.svg)](https://github.com/cvzi/mensahd/actions?query=workflow%3ARunParsersToday) | [32 7-11 * * 1-5](https://crontab.guru/#32_7-11_*_*_1-5 "“At minute 32 past every hour from 7 through 11 on every day-of-week from Monday through Friday.” ") |
| all          | [![RunParsers](https://github.com/cvzi/mensahd/workflows/RunParsers/badge.svg)](https://github.com/cvzi/mensahd/actions?query=workflow%3ARunParsers)                | [12 6 * * *](https://crontab.guru/#12_6_*_*_* "“At 06:12.” ")                                                                                                 |


Links:
*   See the resulting feeds at [https://mensahd.herokuapp.com/api](https://mensahd.herokuapp.com/api)
*   [Understand OpenMensa’s Parser Concept](https://doc.openmensa.org/parsers/understand/)
*   OpenMensa [XML schema](https://doc.openmensa.org/feed/v2/)
*   OpenMensa Android app on [f-droid](https://f-droid.org/en/packages/de.uni_potsdam.hpi.openmensa/), [playstore](https://play.google.com/store/apps/details?id=de.uni_potsdam.hpi.openmensa), [github](https://github.com/domoritz/open-mensa-android)
*   Another parser for OpenMensa: [https://github.com/cvzi/mensa](https://github.com/cvzi/mensa)
