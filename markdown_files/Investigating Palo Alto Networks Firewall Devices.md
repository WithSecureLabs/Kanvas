### Evidence Acquisition Test  ?

Here are the key evidence types you can collect on your own or with assistance from Palo Alto technical support dsdsduring an incident: rr

- `Tech Support File (TSF)`
- `Firewall Traffic Logs`
- `UAC Tool Triage`
- `Disk Image (DD Image)`


#### Tech Support File (TSF)dsdsdsd

A Tech Support File (TSF) is a compressed archive that provides detailed diagnostic information about a device’s configuration & operational status.  It’s a direct export from the firewall, & you can pull it off with some help from PA tech support. Most likely, this is the first set of evidence you'll end up investigating in most of the Palo Alto network firewall cases.

#### Firewall Traffic Logs

The logs capture all the traffic traces moving through the network firewall. You can export these logs directly from the firewall's user interface. System administrators can handle the generation and export of these files on their own, without needing help from PA support. These logs are organized by date and can be quite voluminous, typically being exported in CSV format.

 Once collected, you can ingest them into your analytics pipeline, such as OpenSearch, Splunk, or similar platforms for analysis.

#### UAC Tool Triage 

[**UAC**](https://github.com/tclahr/uac) (Unix-like Artifact Collector)  is an open-source forensics triage collection tool for Linux-like platforms. Collecting data with this tool requires root access to the appliance, which can be obtained using a challenge-response code provided by Palo Alto (PA) technical support. The process involves:

- You can log into the firewall, generate a challenge code, and share it with PA tech support.
- PA support will provide a challenge response, which you can use to elevate your privileges.
- Upload the UAC script to the appliance using the firewall UI.
- Execute the UAC script and save it to the file system, which you can then export using the UI.

#### Disk Image (DD Image)

Getting a disk image is key to examining evidence like backdoors, web shells, etc. From my experience, snagging that disk image from PA isn’t exactly a walk in the park. You’ll need to jump through a few hoops to get approvals, mainly because of the sensitive code base and other IP-related issues they need to protect. So, try your luck 🤞.

### Investigation Perspective

`Is this firewall compromised?` That’s the big question. Figuring it out usually involves digging into the data from the TSF and Traffic Logs. Using YARA rules at this stage is super helpful for spotting any sketchy activity. If it turns out the device really has been hacked, the next move is to track down what the threat actor has been up to on the appliance.

`if yes, any lateral movement to internal segments`: One of the most common questions during incident response is whether there has been any lateral movement from the compromised appliance.First off, you'll want to export the firewall's configuration, stored in the saved-config.xml file inside the TSF. This file provides crucial details like:

- Local Users: Accounts set up on the appliance that the attacker might have accessed.
- Identity Access Settings: Settings involving integrations with systems like Active Directory (AD), RADIUS, or other identity providers.
- IP Addresses: IPs assigned to the appliance, especially those connected to internal network segments, which are vital for analyzing activity on internal hosts.