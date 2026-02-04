# **App Name**: CAPTCHA Crucible

## Core Features:

- CAPTCHA Selection: Enable users to switch between Line CAPTCHA and Visual CAPTCHA challenges via a tab interface.
- Line CAPTCHA Display: Present a canvas element (#captcha-canvas) where users can trace a curved path. This is the challenge area for motor-control based CAPTCHAs.
- Visual CAPTCHA Display: Display one-click abstract puzzles within the same canvas area (#captcha-canvas), providing a perceptual reasoning challenge.
- Challenge Reload: Implement a 'New Challenge' button (#reload-btn) that triggers a new CAPTCHA challenge.
- Status Messaging: Provide real-time feedback to the user via a status message area (#status).
- Timer Display: Display a countdown timer (#timer) to indicate the time remaining to complete the CAPTCHA.

## Style Guidelines:

- Background color: Dark background (#121212) to create a high-contrast, focused environment.
- Primary color: Cyan (#00FFFF) for interactive elements to draw attention and provide a tech-focused aesthetic.
- Accent color: Teal (#008080) to complement the primary, used for hover states and secondary interactive elements.
- Body and headline font: 'Inter', a sans-serif font for a modern and readable UI.
- Center the CAPTCHA challenge area on the screen with a square canvas placeholder.
- Ensure the layout is responsive, adapting to different screen sizes and devices.