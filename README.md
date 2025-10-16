# Backend Wizards — Stage 0 Task

**Author:** Muhammad Ahmad El-kufahn  
**Email:** muhammadelkufahn27@gmail.com  
**Stack:** Python / Django / DRF

---

## Overview

This project implements the **Stage 0 backend task** — a REST API endpoint `/me` that returns:

-  Profile information
-  Current UTC timestamp
-  A random cat fact fetched dynamically from the Cat Facts API

Example response:

```json
{
	"status": "success",
	"user": {
		"email": "muhammadelkufahn27@gmail.com",
		"name": "Muhammad Ahmad El-kufahn",
		"stack": "Python/Django"
	},
	"timestamp": "2025-10-16T10:50:56.518856+00:00",
	"fact": "A cat will tremble or shiver when it is extreme pain."
}
```
