# Flex Counter Policy ATT Comparison

This artifact compares the two C4/C5 flex-counter policies from meeting item 5.

| Scheduler | Flex policy | ATT | First ATT | Business ATT | Economy ATT | Selected |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| ours | Our Scheduler: Weighted HRRN | 19.18 | 20.38 | 21.73 | 17.97 | yes |
| ours_class | Our Scheduler: Class priority + HRRN | 20.74 | 13.38 | 15.36 | 24.55 | no |

Selected policy: `ours` because it has the lower ATT (19.18).
