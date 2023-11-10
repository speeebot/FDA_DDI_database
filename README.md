# FDA_DDI_database
The aim of this project is to develop tools that can efficiently and effectively identify potential drug-drug interactions (DDIs) from the extensive FAERS (FDA Adverse Event Reporting System) database. The database contains over 26 million adverse drug events (ADEs) reported in patients receiving various combinations of medications.

To accomplish this goal, we will utilize the openFDA API to extract drug adverse events from the FAERS database for a specific drug of interest (Drug A). Subsequently, we will investigate potential drug combinations for a frequently observed side effect associated with Drug A.

We will then employ an association rule algorithm to compare the risk of experiencing the side effect when taking Drug A alone versus when taking Drug A in combination with other medications.

The final output will be the DDI index, which is defined as the ratio of the lift value of an association rule {Drug A combinations -> side effect} to the lift value of another association rule {Drug A -> Side effect}. Higher DDI index values indicate a higher likelihood of potential drug-drug interactions.

By utilizing these steps, we aim to develop a reliable tool for identifying potential drug-drug interactions from the FAERS database that can help healthcare professionals make informed decisions about medication therapy and ultimately improve patient safety.
