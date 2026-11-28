# OpenAQ Observation History Plan (A-004)

> **Notice**: This plan outlines historical hourly observation acquisition for Delhi-NCR stations.
> **Note [Unverified]**: OpenAQ v3 documentation does not specify whether `datetime_to` is inclusive.
> Windows are configured with a 1-hour overlap to prevent loss of boundary hourly readings.
> Downstream processing (`features/observations.py`) safely deduplicates all identical timestamps.

## 1. Plan Configuration Summary

- **From Date**: `2024-01-01` (aligned to Jan 2024 weather model coverage)
- **Target Parameters**: `pm25`
- **Window Size**: `35` days (up to 840 hours; fits within 1000-record page)
- **Window Overlap**: 1 hour (`unverified` boundary inclusion)
- **Request Spacing**: `1.1` seconds (strict rate-limit adherence)
- **Max Requests per Run**: `1200`
- **Active 'use' Stations Covered**: 76
- **Distinct Sensors Targeted**: 76
- **Total Target Windows**: 1828
- **Estimated Full Ingestion Duration**: ~33.5 minutes

## 2. Stations Lacking Requested Sensor IDs (Skipped)

All targeted stations possess valid sensor IDs for the requested parameters.

## 3. Targeted Station Windows Summary

| Station ID | Station Name | Area | Parameter | Sensor ID | Windows Planned |
|---|---|---|---|---|---|
| `17` | R K Puram, Delhi - DPCC | `central_delhi` | **pm25** | `12234787` | 31 |
| `50` | Punjabi Bagh, Delhi - DPCC | `central_delhi` | **pm25** | `396` | 31 |
| `235` | Anand Vihar, New Delhi - DPCC | `ghaziabad` | **pm25** | `384` | 31 |
| `301` | Vikas Sadan, Gurugram - HSPCB | `gurugram` | **pm25** | `14258988` | 31 |
| `5404` | Pusa, Delhi - IMD | `central_delhi` | **pm25** | `12234702` | 31 |
| `5541` | Burari Crossing, New Delhi - IMD | `central_delhi` | **pm25** | `12234684` | 31 |
| `5570` | Aya Nagar, New Delhi - IMD | `gurugram` | **pm25** | `12234708` | 31 |
| `5586` | Sirifort, Delhi - CPCB | `central_delhi` | **pm25** | `12234769` | 20 |
| `5598` | Sector - 125, Noida, UP - UPPCB | `noida` | **pm25** | `12235187` | 20 |
| `5610` | North Campus, DU, Delhi - IMD | `central_delhi` | **pm25** | `12234690` | 31 |
| `5613` | ITO, New Delhi - CPCB | `central_delhi` | **pm25** | `12234753` | 31 |
| `5616` | Sector - 62, Noida, UP - IMD | `ghaziabad` | **pm25** | `12234720` | 20 |
| `5622` | NSIT Dwarka, Delhi - CPCB | `gurugram` | **pm25** | `12234744` | 31 |
| `5626` | DTU, New Delhi - CPCB | `central_delhi` | **pm25** | `14985` | 31 |
| `5627` | CRRI Mathura Road, New Delhi - IMD | `central_delhi` | **pm25** | `14935` | 31 |
| `5630` | Shadipur, Delhi - CPCB | `central_delhi` | **pm25** | `12234726` | 31 |
| `5634` | Lodhi Road, New Delhi - IMD | `central_delhi` | **pm25** | `12234714` | 31 |
| `5650` | IGI Airport (T3), Delhi - IMD | `central_delhi` | **pm25** | `12234696` | 20 |
| `5665` | Vasundhara, Ghaziabad - UPPCB | `ghaziabad` | **pm25** | `12235160` | 31 |
| `6356` | Pusa, Delhi - DPCC | `central_delhi` | **pm25** | `12235321` | 20 |
| `6358` | Mandir Marg, New Delhi - DPCC | `central_delhi` | **pm25** | `17770` | 31 |
| `6359` | IHBAS, Dilshad Garden,New Delhi - CPCB | `ghaziabad` | **pm25** | `12234735` | 31 |
| `6924` | Indirapuram, Ghaziabad - UPPCB | `ghaziabad` | **pm25** | `12235779` | 31 |
| `6929` | Major Dhyan Chand National Stadium, Delhi - DPCC | `central_delhi` | **pm25** | `12235047` | 31 |
| `6932` | Alipur, Delhi - DPCC | `central_delhi` | **pm25** | `19935` | 31 |
| `6934` | Dr. Karni Singh Shooting Range, Delhi - DPCC | `faridabad` | **pm25** | `12235011` | 31 |
| `6938` | Vivek Vihar, Delhi - DPCC | `ghaziabad` | **pm25** | `12235133` | 31 |
| `6953` | Sector-2 IMT, Manesar - HSPCB | `gurugram` | **pm25** | `20006` | 31 |
| `6957` | Jawaharlal Nehru Stadium, Delhi - DPCC | `central_delhi` | **pm25** | `20020` | 31 |
| `6960` | Patparganj, Delhi - DPCC | `central_delhi` | **pm25** | `20049` | 31 |
| `6972` | Nathu Colony, Ballabgarh - HSPCB | `faridabad` | **pm25** | `14283600` | 31 |
| `6978` | Knowledge Park - III, Greater Noida - UPPCB | `noida` | **pm25** | `12235196` | 31 |
| `6980` | Sector-1, Noida - UPPCB | `noida` | **pm25** | `12235951` | 31 |
| `6986` | Knowledge Park - V, Greater Noida - UPPCB | `noida` | **pm25** | `12235935` | 31 |
| `6988` | Sector-116, Noida - UPPCB | `noida` | **pm25** | `12235942` | 20 |
| `7005` | Loni, Ghaziabad - UPPCB | `ghaziabad` | **pm25** | `12235787` | 31 |
| `8118` | New Delhi | `central_delhi` | **pm25** | `23534` | 31 |
| `8235` | Jahangirpuri, Delhi - DPCC | `central_delhi` | **pm25** | `12235029` | 31 |
| `8239` | Okhla Phase-2, Delhi - DPCC | `central_delhi` | **pm25** | `12235074` | 31 |
| `8365` | Nehru Nagar, Delhi - DPCC | `central_delhi` | **pm25** | `12235083` | 31 |
| `8472` | Bawana, Delhi - DPCC | `central_delhi` | **pm25** | `36391` | 31 |
| `8915` | Wazirpur, Delhi - DPCC | `central_delhi` | **pm25** | `12235124` | 31 |
| `8917` | Ashok Vihar, Delhi - DPCC | `central_delhi` | **pm25** | `12235002` | 31 |
| `10484` | Sri Aurobindo Marg, Delhi - DPCC | `central_delhi` | **pm25** | `34772` | 31 |
| `10486` | Mundka, Delhi - DPCC | `central_delhi` | **pm25** | `34767` | 31 |
| `10488` | Najafgarh, Delhi - DPCC | `gurugram` | **pm25** | `12235065` | 31 |
| `10820` | Sector 30, Faridabad - HSPCB | `faridabad` | **pm25** | `12236236` | 20 |
| `10825` | Sector-51, Gurugram - HSPCB | `gurugram` | **pm25** | `12236259` | 31 |
| `10900` | Teri Gram, Gurugram - HSPCB | `gurugram` | **pm25** | `12236251` | 31 |
| `10908` | Sector 11, Faridabad - HSPCB | `faridabad` | **pm25** | `12236245` | 31 |
| `10919` | Sanjay Nagar, Ghaziabad - UPPCB | `ghaziabad` | **pm25** | `36675` | 31 |
| `10920` | New Industrial Town, Faridabad - HSPCB | `faridabad` | **pm25** | `12236227` | 20 |
| `11603` | Chandni Chowk, Delhi - IITM | `central_delhi` | **pm25** | `39410` | 31 |
| `11607` | Lodhi Road, Delhi - IITM | `central_delhi` | **pm25** | `39433` | 31 |
| `2860223` | GK1 (Oberoi Terrace) | `central_delhi` | **pm25** | `9320367` | 27 |
| `3024966` | NASA GSFC Rutgers Calib. N8 | `gurugram` | **pm25** | `10326358` | 25 |
| `3410004` | Amity University, Panchgaon - IITM | `gurugram` | **pm25** | `12238725` | 20 |
| `4663956` | Santushti Apartments, Vasant Kunj | `central_delhi` | **pm25** | `13273790` | 17 |
| `4712609` | Air Check | `central_delhi` | **pm25** | `15289075` | 10 |
| `6105800` | Sector 1, Noida extension | `noida` | **pm25** | `14453757` | 13 |
| `6125489` | Uptitude Cloud Pvt Ltd - Sector 62, GGN | `gurugram` | **pm25** | `14598776` | 12 |
| `6145551` | Anand Lok | `central_delhi` | **pm25** | `14745878` | 12 |
| `6148686` | IIT Delhi, Delhi - IITM | `central_delhi` | **pm25** | `14769474` | 11 |
| `6254594` | Talkatora Garden, Delhi - DPCC | `central_delhi` | **pm25** | `15554208` | 9 |
| `6254663` | JNU, Delhi - DPCC | `central_delhi` | **pm25** | `15554704` | 9 |
| `6254664` | NSUT Jaffarpur, Delhi - DPCC | `gurugram` | **pm25** | `15554716` | 9 |
| `6254665` | Commonwealth Sports Complex, Delhi - DPCC | `central_delhi` | **pm25** | `15554728` | 9 |
| `6254666` | IGNOU_Maidan Garhi, Delhi - DPCC | `central_delhi` | **pm25** | `15554740` | 9 |
| `6257818` | Cantonment Area, Delhi - DPCC | `central_delhi` | **pm25** | `15578291` | 9 |
| `6299494` | Prashant Garden, Khora - UPPCB | `noida` | **pm25** | `15888918` | 8 |
| `6299603` | SRM University, Modinagar - UPPCB | `ghaziabad` | **pm25** | `15889770` | 8 |
| `6299678` | Ved Vihar-Loni, Ghaziabad - UPPCB | `central_delhi` | **pm25** | `15890341` | 8 |
| `6311324` | Govindpuram, Ghaziabad - UPPCB | `ghaziabad` | **pm25** | `15978433` | 8 |
| `6458520` | Wave City, Ghaziabad - UPPCB | `ghaziabad` | **pm25** | `17025422` | 5 |
| `6551511` | Sector-26, Noida | `noida` | **pm25** | `17767060` | 2 |
| `6551581` | Anahad Foundation | `noida` | **pm25** | `17767473` | 2 |
