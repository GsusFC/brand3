# Visual Signature Dismissal Audit

Evidence-quality diagnostics only. Raw viewport remains the primary evidence.

- Total results: 5
- Dismissal attempts: 1
- Successful dismissals: 0
- Failed dismissals: 1
- Dismissal success rate: 0.0%
- Mutation summary: {"attempted": 1, "failed": 1, "success_rate": 0.0, "successful": 0}

## Severity Transitions

- Before: {"blocking": 5}
- After: {"blocking": 5}
- Eligibility: {"eligible": 4, "none": 1}
- Block reasons: {"no_safe_close_button_found": 2, "no_safe_cookie_button_found": 1, "none": 2}
- Perceptual states: {"OBSTRUCTED_STATE": 3, "REVIEW_REQUIRED_STATE": 1, "UNSAFE_MUTATION_BLOCKED": 1}
- Transition reasons: {"exact_safe_affordance_detected": 1, "low_confidence_obstruction": 4, "no_safe_affordance_detected": 3, "protected_environment_detected": 1, "raw_capture_created": 5, "safe_mutation_attempted": 1, "safe_mutation_failed": 1}
- Affordance categories: {"ambiguous_action": 11, "close_control": 4, "login_action": 4, "subscription_action": 1, "unknown_action": 543}
- Interaction policies: {"requires_human_review": 554, "safe_to_dismiss": 4, "unsafe_to_mutate": 5}
- Affordance owners: {"active_obstruction": 7, "header_navigation": 90, "social_link": 28, "unknown_owner": 423, "unrelated_cart_drawer": 7, "unrelated_chat_widget": 8}
- Safe-to-dismiss candidates not clicked: 2
- Unsafe-to-mutate candidates encountered: 5
- Requires-human-review candidates encountered: 554

## Material Viewport Changes

- Allbirds (https://www.allbirds.com)

## Failed Dismissals

| Brand | Method | Clicked Text | Before | After |
| --- | --- | --- | --- | --- |
| Allbirds | close | Close | blocking | blocking |
