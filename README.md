
<br />
<div align="center">
    <img src="images/logo.png" alt="Logo" width="80" height="80">
  </a>
  <h1 align="center">Kanvas</h1>
</div>

**KANVAS**  is an IR (incident response) case management tool with an intuitive desktop interface, built using Python. It provides a unified workspace for investigators working with SOD (Spreadsheet of Doom) or similar spreadsheets, enabling key workflows to be completed without switching between multiple applications.
<img src="assets/kanvas_demo.gif" alt="Logo">

## ✨ Key Features

### 🎲 **Case Management**
- **Built on the SOD (Spreadsheet of Doom)**: All data remains within the spreadsheet, making distribution and collaboration simple—even outside the application.
- **Multi-User support**: Files can reside on local machines or shared drives, enabling active collaboration among multiple investigators. File locking ensures that editing is properly managed and conflicts are avoided.
- **One-Click Sanitize**: Allows spreadsheet data—such as domains, URLs, IP addresses, etc.—to be sanitized with a single click, making it easy to share and store.

> [!TIP]
> The `SOD` template is slightly modified. Use the included `sod.xlsx` file from the package.

### 📊 **Data Visualization**

- 📌**Attack Chain Visualization**: Visualizes lateral movement for quick review of the adversary’s attack path. The re-draw options help display the diagram in multiple ways.
- 📌**Incident Timeline**: The incident timeline is presented in chronological order, helping investigators quickly understand the sequence and timing of the overall incident.
- 📌**MITRE Flow Builder**: Lets you visualize & share sequences of adversary actions. You can populate flows with attacker TTP, then link them to map the sequence of techniques seen during an incident..
- **Export for Reporting**: The lateral movement & timeline visualizations can be exported as image files or CSV, allowing direct use in presentations or investigation reports.

>[!TIP]
> Ensure the following column names exist and match exactly if you're using your own spreadsheet.

```text
SOD Spreadsheets/
├── Timeline/
│   ├── Timestamp_UTC_0
│   ├── EvidenceType
│   ├── Event System
│   ├── <->
│   ├── Remote System
│   ├── MITRE Tactic
│   ├── MITRE Techniques
│   └── Visualize
└──  Systems/
    ├── HostName
    ├── IPAddress
    └── SystemType
```

### 👀 **Threat Intelligence Lookups**

- **IP Reputation**: IP reputation, geolocation, open ports, known vulnerabilities, and more using various API integrations.
- **Domain / URL Insights**: WHOIS data, DNS records, and more using various API integrations.
- **File Hash Insights**: Lookup binary file insights on various platforms based on hash values.
- **CVE Insights**: Information on known exploit usage based on CISA and other vulnerability intelligence sources.
- **Email Insights**: Information on whether the email address has appeared in any known data breaches.
- 📌**Ransomware Victim**: Verify if a customer or organization’s data has been published online following a ransomware attack.

>[!TIP]
> Configure API keys such as VirusTotal, Shodan, and others—before using the lookup features.

### 🛡️ **Security Framework Mapping**

- **MITRE ATT&CK Mapping**: Provides up-to-date MITRE tactics and techniques for mapping adversary activities.
- 📌**MITRE D3FEND Mapping**: Helps map defense strategies based on the identified ATT&CK techniques. This is especially useful when responding to an incident from a defender’s perspective.
- **V.E.R.I.S. Reporting**: Provides an interface to track VERIS data, which can be shared post-incident with various government entities and contribute to the Verizon Data Breach Report.

### 📑 **Knowledge Management**

- **Bookmarks**: Offers a curated list of security tool, an up-to-date list of Microsoft portal URLs, and the ability to create custom investigation-specific bookmarks.
- 📌**Markdown Editor**: Provides an interface to create and update Markdown documents—ideal for note-taking or loading investigative playbooks during investigations.
- **Event ID Reference**: Consolidates Windows Event IDs in one place, organized by categories like persistence, lateral movement, and more—making it easy to cross-reference during investigations.
- **Entra ID Reference**: Provides a searchable list of known and malicious Microsoft Entra ID AppIDs—useful for investigating Business Email Compromise (BEC) cases.
- **Living Off the Land Binaries**: Provides a searchable list of known Microsoft living-off-the-land (LOLBAS) binaries that threat actors have abused.
- **Microsoft Azure Portals**: Provides a searchable list of constantly changing Microsoft Azure / Entra URLs, useful when responding to Azure cloud incidents.
  
> [!TIP]
> For easy access, keep all Markdown files in the `markdown_files` folder.
---

## 🚀 Installation

1. **Clone the Repository**
   ```bash
   git clone https://github.com/WithSecureLabs/Kanvas.git
   cd Kanvas
   ```

2. **Create Virtual Environment**
   ```bash
   # On Windows 
   python3 -m venv venv
   venv\Scripts\activate

   # On MacOs / Linux
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install Dependencies**
   ```bash
   pip3 install -r requirements.txt
   ```

4. **Run KANVAS**
   ```bash
   python3 kanvas.py
   ```

> [!IMPORTANT]
> When using the tool for the first time, ensure that you download the latest updates by clicking on `Download Updates`.
---

## ⚠️Notes

- The `incident timeline` logic only works if you’ve mapped the MITRE TTPs in the timeline sheet for each entry.
- MITRE `Flow Builder` uses QT WebBrowser (Chromium-based). It may sometimes have performance issues, especially on Windows.

## Acknowledgements

 - [Publicly disclosed ransomware victim data](https://www.ransomware.live/about) by [Julien Mousqueton](https://www.linkedin.com/in/julienmousqueton/)
 - [Microsoft First Party App Names & Graph Permissions](https://github.com/merill/microsoft-info) by [Merill Fernando ](https://www.linkedin.com/in/merill/)
 - [Curated list of Microsoft portals](https://msportals.io/about/) by ([Adam Fowler](https://www.linkedin.com/in/adamfowlerit/))
---
