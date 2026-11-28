# Google Play Console Account & Closed Testing Tracker (A-007)

> **Privacy Notice**: This repository never stores personal data, real names, email addresses, phone numbers, identity numbers, or payment credentials. The master tester registry, fee receipts, and developer identity verification records are stored strictly outside this repository in secure local storage.

---

## 1. Google Play Developer Account Setup & Verification Checklist

| Item | Requirement | Status | Notes |
|---|---|---|---|
| **Account Type** | Personal Developer Account | Pending Registration | Owner: Pramod Kumar |
| **Registration Date** | Date registration submitted | `[YYYY-MM-DD]` | Recorded upon console creation |
| **Registration Fee Receipt** | Payment receipt for \$25 USD fee | Stored Offline | Receipts kept in offline records outside git |
| **Identity Verification** | Government ID & selfie verification | Pending | Standard Google Play personal account requirement |
| **2-Step Verification** | Enabled on developer Google account | Required | Security requirement for console access |
| **D-U-N-S Number** | Organization verification | Not Applicable | Only required for Organization accounts |
| **Play Console Access** | Console dashboard active | Pending | Verified once account verification passes |

---

## 2. 14-Day Continuous Closed Testing Clock

### Google Play Policy Requirement
- **Policy Rule**: Google Play requires personal developer accounts to run a closed test with at least **12 testers opted in continuously for at least 14 days** before applying for production access.
- **Recruitment Buffer Target**: Recruit **20 testers** (to provide an 8-person safety margin against accidental uninstalls or opt-outs during the 14-day window).

### Closed Testing Date Calculator Table

| Test Start Date (Day 1) | Day 14 Continuous Opt-in Complete | Earliest Production Access Request Date |
|---|---|---|
| `2026-12-01` | `2026-12-14` | `2026-12-15` |
| `2026-12-08` | `2026-12-21` | `2026-12-22` |
| `2026-12-15` | `2026-12-28` | `2026-12-29` |
| `2026-12-22` | `2027-01-04` | `2027-01-05` |
| `2027-01-01` | `2027-01-14` | `2027-01-15` |

---

## 3. Tester Recruitment Messages

### English Version
> **Subject**: Invitation to test NCR Hawa: Honest Delhi-NCR Air Quality Forecasts
> 
> Hi! I am building **NCR Hawa**, a lightweight, honest air quality forecast app for Delhi-NCR that provides reliable D+1 and D+2 forecasts with transparent baselines.
> 
> To launch on the Google Play Store, Google requires 12 testers to install the app and keep it on their phones for 14 continuous days.
> 
> If you live or travel in Delhi-NCR and use an Android phone:
> 1. Reply with your Google Play email address (kept completely private).
> 2. Opt in via the closed-test link I send you and install the app.
> 3. Keep the app installed for 14 days and open it occasionally to check the forecast.
> 
> No accounts, no ads, no trackers. Thank you for helping bring honest air forecasts to Delhi!

### Hindi Version (हिंदी)
> **विषय**: 'NCR हवा' ऐप टेस्टिंग आमंत्रण: दिल्ली-एनसीआर का पारदर्शी वायु गुणवत्ता पूर्वानुमान
> 
> नमस्ते! मैं **'NCR हवा' (NCR Hawa)** ऐप बना रहा हूँ, जो दिल्ली-एनसीआर के लिए अगले 1-2 दिनों का सटीक और पारदर्शी वायु गुणवत्ता (AQI) पूर्वानुमान प्रदान करता है। इसमें कोई विज्ञापन, अकाउंट या ट्रैकर नहीं है।
> 
> गूगल प्ले स्टोर पर ऐप प्रकाशित करने के लिए, गूगल की नीति के अनुसार कम से कम 12 टेस्टर्स को 14 दिनों तक ऐप इंस्टॉल रखना आवश्यक है।
> 
> यदि आप दिल्ली-एनसीआर में रहते हैं और एंड्रॉइड फोन इस्तेमाल करते हैं, तो कृपया टेस्टिंग में सहयोग करें:
> 1. अपना गूगल प्ले ईमेल मुझे भेजें (यह पूरी तरह निजी रहेगा)।
> 2. टेस्टिंग लिंक से ऐप इंस्टॉल करें।
> 3. ऐप को 14 दिनों तक फोन में रखें और बीच-बीच में पूर्वानुमान देखें।
> 
> आपका सहयोग दिल्ली-एनसीआर को पारदर्शी हवा का पूर्वानुमान देने में बहुत मददगार होगा। धन्यवाद!

---

## 4. Anonymized Tester Tracking Table

> **Note**: Only tester initials and device specifications are recorded here. The master list with email addresses is maintained strictly outside the repository.

| Tester ID | Initials | Phone Model | Android Version | Opt-in Date | 14-Day Mark | Still Opted In? | Notes |
|---|---|---|---|---|---|---|---|
| `T-01` | PK | Pixel 7 | Android 14 | `YYYY-MM-DD` | `YYYY-MM-DD` | Yes | Primary internal tester |
| `T-02` | AS | Samsung Galaxy S22 | Android 14 | `YYYY-MM-DD` | `YYYY-MM-DD` | Yes | Central Delhi |
| `T-03` | RK | OnePlus 11R | Android 13 | `YYYY-MM-DD` | `YYYY-MM-DD` | Yes | Noida |
| `T-04` | VS | Xiaomi Redmi Note 12 | Android 13 | `YYYY-MM-DD` | `YYYY-MM-DD` | Yes | Gurugram |
| `T-05` | MD | Motorola Edge 40 | Android 14 | `YYYY-MM-DD` | `YYYY-MM-DD` | Yes | Faridabad |
| `T-06` | NG | Realme GT 2 | Android 13 | `YYYY-MM-DD` | `YYYY-MM-DD` | Yes | Ghaziabad |
| `T-07` | SK | Samsung Galaxy A54 | Android 14 | `YYYY-MM-DD` | `YYYY-MM-DD` | Yes | South Delhi |
| `T-08` | AB | Vivo V27 | Android 13 | `YYYY-MM-DD` | `YYYY-MM-DD` | Yes | West Delhi |
| `T-09` | PT | Pixel 6a | Android 14 | `YYYY-MM-DD` | `YYYY-MM-DD` | Yes | North Delhi |
| `T-10` | RM | Poco X5 Pro | Android 13 | `YYYY-MM-DD` | `YYYY-MM-DD` | Yes | Gurugram |
| `T-11` | ST | OnePlus Nord CE 3 | Android 13 | `YYYY-MM-DD` | `YYYY-MM-DD` | Yes | East Delhi |
| `T-12` | VK | Samsung Galaxy M34 | Android 13 | `YYYY-MM-DD` | `YYYY-MM-DD` | Yes | Noida |
| `T-13` | DB | Pixel 8 | Android 14 | `YYYY-MM-DD` | `YYYY-MM-DD` | Yes | Backup tester |
| `T-14` | SM | Xiaomi 12 Pro | Android 14 | `YYYY-MM-DD` | `YYYY-MM-DD` | Yes | Backup tester |
| `T-15` | KK | Samsung Galaxy S21 FE | Android 14 | `YYYY-MM-DD` | `YYYY-MM-DD` | Yes | Backup tester |
| `T-16` | AJ | Realme 11 Pro | Android 13 | `YYYY-MM-DD` | `YYYY-MM-DD` | Yes | Backup tester |
| `T-17` | PS | Motorola G84 | Android 13 | `YYYY-MM-DD` | `YYYY-MM-DD` | Yes | Backup tester |
| `T-18` | HS | Vivo Y200 | Android 13 | `YYYY-MM-DD` | `YYYY-MM-DD` | Yes | Backup tester |
| `T-19` | RS | OnePlus 10T | Android 14 | `YYYY-MM-DD` | `YYYY-MM-DD` | Yes | Backup tester |
| `T-20` | NK | Samsung Galaxy A34 | Android 14 | `YYYY-MM-DD` | `YYYY-MM-DD` | Yes | Backup tester |
