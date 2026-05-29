# TLDR Brand3 Research Pack evaluation

- Dataset version: `tldr_brand3_research_pack_dataset_v0_1`
- Gold version: `tldr_brand3_research_pack_gold_v0_1`
- Cases evaluated: `7`

## Summary
- Legacy scanner strategic usefulness: `62.6`
- Analyst Pass strategic usefulness: `77.2`
- Delta: `+14.6`

### Biggest block gains
- `attributes`: `+27.9`
- `values`: `+27.4`
- `personality`: `+21.1`

### Cases where the Analyst Pass worsens
- None in this benchmark set.

### Next adjustments
- Tighten noise rejection before block interpretation; chrome, feed, and article fragments still leak into the legacy scanner.
- Degrade confidence more aggressively when outputs move from inferred evidence to declared language without owned support.
- Strengthen the brand-idea synthesis rule so weak conceptual glue is marked reviewable instead of promoted as strategic fact.
- Require the value proposition block to preserve the audience when the manual gold notes make it explicit.

## Case summary

| case               | scanner | analyst | delta | benchmark taxonomy                                                                         | scanner taxonomy                                        | analyst taxonomy                                       |
| ------------------ | ------- | ------- | ----- | ------------------------------------------------------------------------------------------ | ------------------------------------------------------- | ------------------------------------------------------ |
| base44.com         | 47.2    | 57.5    | +10.3 | concept_not_inferred, entity_context_not_promoted, proof_point_as_personality              | missing_audience, overclaim, proof_point_as_personality | overclaim, proof_point_as_personality, weak_brand_idea |
| bokeroon.com       | 60.1    | 100.0   | +39.9 | attributes_under_extracted, brand_idea_weak_but_not_absent, feed_or_article_noise          | overclaim, weak_brand_idea                              | —                                                      |
| fly.io             | 76.4    | 77.9    | +1.6  | —                                                                                          | overclaim, weak_brand_idea                              | weak_brand_idea                                        |
| every.to/about     | 68.7    | 72.6    | +4.0  | —                                                                                          | overclaim, weak_brand_idea                              | weak_brand_idea                                        |
| lab.naturaumana.ai | 60.2    | 69.3    | +9.1  | audited_surface_too_narrow, parent_entity_not_expanded, product_surface_used_as_full_brand | entity_context_missing, overclaim, weak_brand_idea      | overclaim, weak_brand_idea                             |
| creatify.ai/es/    | 63.1    | 63.1    | 0.0   | —                                                                                          | false_vision, missing_audience, overclaim               | false_vision, missing_audience, overclaim              |
| www.heygen.com     | n/a     | 100.0   | n/a   | missing_scanner_scan                                                                       | —                                                       | —                                                      |

## Block summary

| block             | scanner | analyst | delta | noise delta |
| ----------------- | ------- | ------- | ----- | ----------- |
| core_purpose      | 61.8    | 74.8    | +13.0 | 0.0         |
| magnetism         | 82.4    | 84.6    | +2.2  | +6.7        |
| value_proposition | 64.2    | 76.9    | +12.7 | +6.7        |
| personality       | 55.6    | 76.7    | +21.1 | 0.0         |
| brand_idea        | 59.3    | 76.1    | +16.8 | 0.0         |
| attributes        | 51.0    | 78.9    | +27.9 | 0.0         |
| values            | 42.9    | 70.3    | +27.4 | 0.0         |
| mission           | 70.5    | 75.0    | +4.5  | 0.0         |
| vision            | 75.8    | 81.8    | +6.0  | 0.0         |

## Detailed case tables

### `https://base44.com`

Benchmark regression case. Base44 is the clearest example of structural noise and founder-proof over-promotion in the old scanner.

Gold summary: Democratize software creation with natural-language app building. Avoid chrome and founder-proof over-weighting.
Dataset difference note: Manual reading favors the owned offer and mission; the current scanner over-weights chrome and founder proof.

| block             | gold                                                       | scanner                                                   | analyst                                                    | scanner score | analyst score | delta | scanner tags                                | analyst tags               |
| ----------------- | ---------------------------------------------------------- | --------------------------------------------------------- | ---------------------------------------------------------- | ------------- | ------------- | ----- | ------------------------------------------- | -------------------------- |
| core_purpose      | democratize software creation by letting people turn idea… | partner with base44 to help students create and innovate. | base44 exists to make app creation simple for non-technic… | 67.1          | 60.4          | -6.6  | overclaim                                   | overclaim                  |
| magnetism         | built for builders, powered by possibility.                | our mission, your vision.                                 | build and ship apps fast.                                  | 47.5          | 57.4          | +9.9  | overclaim, structural_noise_selected        | overclaim                  |
| value_proposition | base44 lets builders, founders, and teams turn natural la… | our mission, your vision top of page # about us...        | an ai app builder for non-technical founders that reduces… | 37.4          | 73.5          | +36.1 | missing_audience, structural_noise_selected | —                          |
| personality       | builder-first, empowering, fast, anti-friction, practical. | solo founder, $80m exit, 6 months...                      | the founder story makes base44 feel ambitious and builder… | 55.8          | 75.1          | +19.3 | overclaim, proof_point_as_personality       | proof_point_as_personality |
| brand_idea        | software creation becomes a conversation; intent becomes…  | none                                                      | none                                                       | 27.5          | 27.5          | 0.0   | weak_brand_idea                             | weak_brand_idea            |
| attributes        | fast, accessible, full-stack, conversational, practical.   | none                                                      | fast, simple, and ai-first.                                | 27.5          | 63.2          | +35.7 | weak_brand_idea                             | —                          |
| values            | accessibility, autonomy, creative agency, speed, removing… | none                                                      | simplicity, speed, and trust.                              | 27.5          | 63.0          | +35.5 | weak_brand_idea                             | —                          |
| mission           | help anyone create their own apps with zero hassle.        | help anyone create their own apps with zero hassle        | to help teams ship software.                               | 99.9          | 62.8          | -37.1 | —                                           | —                          |
| vision            | move from buying or manually coding software to creating…  | none                                                      | none                                                       | 35.0          | 35.0          | 0.0   | weak_brand_idea                             | weak_brand_idea            |

### `https://bokeroon.com`

Benchmark regression case. Feed/article predictions should remain noise; attributes and clarity language matter.

Gold summary: Keep feed/article predictions out of vision; preserve clarity and transparency signals.
Dataset difference note: Manual reading preserves the offer and extracts clarity/instant/transparency signals. The old scanner treated a rhetorical question as purpose.

| block             | gold                                                       | scanner                                                    | analyst                                                    | scanner score | analyst score | delta | scanner tags    | analyst tags |
| ----------------- | ---------------------------------------------------------- | ---------------------------------------------------------- | ---------------------------------------------------------- | ------------- | ------------- | ----- | --------------- | ------------ |
| core_purpose      | make crypto investing easier to understand and manage for… | ¿listo para simplificar tus inversiones en criptomonedas?  | make crypto investing easier to understand and manage for… | 66.2          | 100.0         | +33.8 | overclaim       | —            |
| magnetism         | menos complicaciones, más claridad.                        | menos complicaciones, más claridad.                        | menos complicaciones, más claridad.                        | 100.0         | 100.0         | 0.0   | —               | —            |
| value_proposition | bokeroon is building a platform that turns crypto managem… | en bokeroon estamos creado una plataforma que convierte l… | bokeroon is building a platform that turns crypto managem… | 79.2          | 100.0         | +20.8 | —               | —            |
| personality       | urgent, encouraging, challenger-like, educational.         | none                                                       | urgent, encouraging, challenger-like, educational.         | 27.5          | 100.0         | +72.5 | weak_brand_idea | —            |
| brand_idea        | crypto management without opacity.                         | none                                                       | crypto management without opacity.                         | 35.0          | 100.0         | +65.0 | weak_brand_idea | —            |
| attributes        | clear, fast, transparent, simple.                          | none                                                       | clear, fast, transparent, simple.                          | 27.5          | 100.0         | +72.5 | weak_brand_idea | —            |
| values            | clarity, accessibility, practical control.                 | none                                                       | clarity, accessibility, practical control.                 | 27.5          | 100.0         | +72.5 | weak_brand_idea | —            |
| mission           | build a platform that makes crypto management instant and… | en bokeroon estamos creado una plataforma que convierte l… | build a platform that makes crypto management instant and… | 78.1          | 100.0         | +21.9 | —               | —            |
| vision            | —                                                          | none                                                       | none                                                       | 100.0         | 100.0         | 0.0   | —               | —            |

### `https://fly.io`

Benchmark target: the strategist pass is close, but the dataset records the current scan and the strategist reading separately.

Gold summary: Preserve strategist-quality synthesis and avoid over-metaphorizing the brand idea.
Dataset difference note: Fly is largely solved; the main residual risk is overclaiming the conceptual idea if evidence gets too metaphorical.

| block             | gold                                                       | scanner                                                    | analyst                                                    | scanner score | analyst score | delta | scanner tags    | analyst tags    |
| ----------------- | ---------------------------------------------------------- | ---------------------------------------------------------- | ---------------------------------------------------------- | ------------- | ------------- | ----- | --------------- | --------------- |
| core_purpose      | get infrastructure out of developers' way so they can shi… | the platform for devs who just want to ship.               | to get out of the way of developers so they can focus ent… | 70.9          | 86.7          | +15.8 | overclaim       | —               |
| magnetism         | build fast. run any code fearlessly.                       | build fast. run any code fearlessly.                       | build fast. run any code fearlessly.                       | 96.0          | 96.0          | 0.0   | —               | —               |
| value_proposition | fly.io gives developers a public cloud for running apps a… | a developer cloud platform for shipping and running code…  | for developers and security engineers, fly.io offers a pu… | 76.6          | 68.1          | -8.4  | —               | —               |
| personality       | technical, playful, dev-native, irreverent.                | the brand projects a bold, playful, and highly technical…  | bold, highly technical, and playfully anti-corporate. it…  | 56.0          | 65.4          | +9.4  | overclaim       | —               |
| brand_idea        | infrastructure as an invisible superpower.                 | the conceptual brand idea frames infrastructure as an emp… | infrastructure as an invisible superpower. the brand posi… | 77.9          | 80.2          | +2.2  | weak_brand_idea | weak_brand_idea |
| attributes        | developer-first, secure, fast, pragmatic.                  | ['developer-first', 'pragmatic']                           | developer-centric, secure-by-default, and pragmatic.       | 69.5          | 74.3          | +4.8  | overclaim       | —               |
| values            | fairness, transparency, developer empathy.                 | ['fairness', 'transparency', 'developer empathy']          | empathy and transparency. the brand actively defends deve… | 76.3          | 63.1          | -13.2 | overclaim       | —               |
| mission           | run apps and code on globally distributed, hardware-isola… | provides developer infrastructure for deploying and runni… | runs containers as lightweight, hardware-isolated virtual… | 64.3          | 67.7          | +3.4  | —               | —               |
| vision            | —                                                          | none                                                       | none                                                       | 100.0         | 100.0         | 0.0   | —               | —               |

### `https://every.to/about`

Multi-surface brand: publication + software + services. The dataset preserves that entity architecture instead of flattening it into a newsletter only.

Gold summary: Treat Every as a multi-surface entity: publication + software + services.
Dataset difference note: The manual reading and strategist pass are close; the key evaluation axis is whether the multi-surface entity architecture remains intact.

| block             | gold                                                       | scanner                                                    | analyst                                                    | scanner score | analyst score | delta | scanner tags    | analyst tags    |
| ----------------- | ---------------------------------------------------------- | ---------------------------------------------------------- | ---------------------------------------------------------- | ------------- | ------------- | ----- | --------------- | --------------- |
| core_purpose      | help people think about what comes next in technology and… | we hope our answers inspire you to ask and answer this qu… | to inspire audiences to think new thoughts and dream new…  | 73.1          | 83.1          | +10.0 | overclaim       | —               |
| magnetism         | what comes next?                                           | “what comes next?” is the question that we try to answer…  | the only subscription you need to stay at the edge of ai   | 79.9          | 68.0          | -11.9 | —               | —               |
| value_proposition | every gives founders, operators, investors, and ai-native… | sign in subscribe *]:block [&>*]:mt-2 [&>*]:pt-2 mt-4" >…  | every provides newsletters, software, courses, and consul… | 68.4          | 72.8          | +4.4  | —               | —               |
| personality       | thoughtful, curious, collaborative, non-dogmatic.          | a collaborative peer that avoids dictating absolute answe… | collaborative, inquisitive, and practical, acting as a pe… | 62.9          | 60.5          | -2.4  | —               | —               |
| brand_idea        | an editorial and product studio for thinking at the edge…  | conceptually framed around operating at the extreme bound… | a collaborative laboratory at the frontier of ai, mapping… | 75.1          | 74.7          | -0.4  | weak_brand_idea | weak_brand_idea |
| attributes        | ai-native, practical, editorial.                           | ['ai-native', 'practical', 'editorial']                    | ai-native, practical, exploratory                          | 76.0          | 78.1          | +2.1  | overclaim       | —               |
| values            | curiosity, usefulness, intellectual independence, experim… | ['inspiration']                                            | privacy and open-source collaboration                      | 50.2          | 59.4          | +9.3  | overclaim       | —               |
| mission           | publish, build, teach, and consult around emerging techno… | the truth is that by answering this question, over and ov… | to publish a daily newsletter, build software products, o… | 61.7          | 69.0          | +7.3  | —               | —               |
| vision            | help people ask and answer what comes next so new technol… | how we run a 25-person c ompany on four ai agents how eve… | a future where answering 'what comes next' collaborativel… | 70.5          | 88.2          | +17.7 | —               | —               |

### `https://lab.naturaumana.ai`

Subdomain / product-surface case. Parent entity expansion matters; the product surface alone underreads purpose and vision.

Gold summary: Subdomain/product surface. Parent entity expansion matters before stronger purpose or vision claims.
Dataset difference note: The current scanner is directionally good, but the dataset keeps the parent-brand context explicit so subdomain inference remains reviewable.

| block             | gold                                                       | scanner                                                    | analyst                                                    | scanner score | analyst score | delta | scanner tags               | analyst tags    |
| ----------------- | ---------------------------------------------------------- | ---------------------------------------------------------- | ---------------------------------------------------------- | ------------- | ------------- | ----- | -------------------------- | --------------- |
| core_purpose      | make personal ai feel more human, useful, and integrated…  | none                                                       | none                                                       | 27.5          | 27.5          | 0.0   | weak_brand_idea            | weak_brand_idea |
| magnetism         | life orchestration, perfected by nature.                   | life orchestration, perfected by nature.                   | life orchestration, perfected by nature.                   | 75.0          | 75.0          | 0.0   | overclaim                  | overclaim       |
| value_proposition | tinynature acts as a personal ai assistant and command ce… | your personal ai assistant for life orchestration. it del… | a personal ai assistant that acts as a centralized comman… | 70.9          | 71.1          | +0.2  | —                          | —               |
| personality       | personal, calm, always-available, companion-like.          | the brand adopts the persona of a personal, always-availa… | an always-on, highly capable companion that balances the…  | 73.5          | 77.7          | +4.3  | —                          | —               |
| brand_idea        | life orchestration through a nature-inspired ai operating… | the conceptual framework is a centralized command center…  | the ai as a centralized command center that moves beyond…  | 66.2          | 76.1          | +9.9  | overclaim, weak_brand_idea | weak_brand_idea |
| attributes        | private, orchestrated, agentic, personal.                  | ['secure', 'security']                                     | secure, highly integrated, and orchestrating.              | 48.6          | 79.8          | +31.2 | overclaim                  | —               |
| values            | privacy, usefulness, personalization, calm intelligence.   | ['security']                                               | data privacy and security.                                 | 48.6          | 78.9          | +30.3 | overclaim                  | —               |
| mission           | build ai assistants and agents that help people coordinat… | natura umana is a revolutionary ai platform that offers p… | to build personal ai agents and platforms that provide us… | 61.5          | 67.7          | +6.2  | entity_context_missing     | —               |
| vision            | unclear from the product surface alone; likely needs pare… | none                                                       | none                                                       | 70.0          | 70.0          | 0.0   | entity_context_missing     | —               |

### `https://creatify.ai/es/`

High-signal performance marketing case. The brand is mostly stable; the main risk is collapsing proof points into the core offer.

Gold summary: Performance marketing platform with strong proof and future-direction language; keep proof separate from core offer.
Dataset difference note: Current TLDR is usable. Manual reading keeps proof points, audience and outcome separated from the core offer.

| block             | gold                                                       | scanner                                                    | analyst                                                    | scanner score | analyst score | delta | scanner tags            | analyst tags            |
| ----------------- | ---------------------------------------------------------- | ---------------------------------------------------------- | ---------------------------------------------------------- | ------------- | ------------- | ----- | ----------------------- | ----------------------- |
| core_purpose      | help marketers and growth teams generate winning ad creat… | creatify está construyendo la capa autónoma de optimizaci… | creatify está construyendo la capa autónoma de optimizaci… | 66.1          | 66.1          | 0.0   | overclaim               | overclaim               |
| magnetism         | anuncios de ia que ganan.                                  | anuncios de ia que ganan.                                  | anuncios de ia que ganan.                                  | 96.0          | 96.0          | 0.0   | —                       | —                       |
| value_proposition | creatify is an ai ad platform designed for performance, l… | the concrete value exchange offers massive cost reduction… | the concrete value exchange offers massive cost reduction… | 52.6          | 52.6          | 0.0   | missing_audience        | missing_audience        |
| personality       | performance-driven, direct, ambitious.                     | the brand projects a revolutionary and highly efficient p… | the brand projects a revolutionary and highly efficient p… | 58.0          | 58.0          | 0.0   | —                       | —                       |
| brand_idea        | an autonomous creative optimization layer for paid media.  | the conceptual brand idea centers on instantly transformi… | the conceptual brand idea centers on instantly transformi… | 74.1          | 74.1          | 0.0   | weak_brand_idea         | weak_brand_idea         |
| attributes        | fast, scalable, performance-oriented, ad-native.           | ['performance']                                            | ['performance']                                            | 56.8          | 56.8          | 0.0   | overclaim               | overclaim               |
| values            | performance, efficiency, automation.                       | none                                                       | none                                                       | 27.5          | 27.5          | 0.0   | weak_brand_idea         | weak_brand_idea         |
| mission           | generate, test, personalize, and optimize ad creatives at… | the concrete value exchange offers massive cost reduction… | the concrete value exchange offers massive cost reduction… | 57.8          | 57.8          | 0.0   | —                       | —                       |
| vision            | every ad and customer touchpoint eventually becomes dynam… | the vision is a future where all customer touchpoints are… | the vision is a future where all customer touchpoints are… | 79.2          | 79.2          | 0.0   | false_vision, overclaim | false_vision, overclaim |

### `https://www.heygen.com`

HeyGen exists in Brand Audit output but not in the current magnetism scan table. The dataset keeps it as a research-pack-only case.

Gold summary: Good scan quality, but no current magnetism scan exists in the corpus. Keep the case as audit-only.
Dataset difference note: The case is still useful for evaluation, but there is no current magnetism scan to compare against.

| block             | gold                                                       | scanner | analyst                                                    | scanner score | analyst score | delta | scanner tags | analyst tags |
| ----------------- | ---------------------------------------------------------- | ------- | ---------------------------------------------------------- | ------------- | ------------- | ----- | ------------ | ------------ |
| core_purpose      | make video creation and localization easy enough for team… | —       | make video creation and localization easy enough for team… | n/a           | 100.0         | n/a   | —            | —            |
| magnetism         | video creation, without the studio bottleneck.             | —       | video creation, without the studio bottleneck.             | n/a           | 100.0         | n/a   | —            | —            |
| value_proposition | heygen lets teams create talking-avatar videos and locali… | —       | heygen lets teams create talking-avatar videos and locali… | n/a           | 100.0         | n/a   | —            | —            |
| personality       | polished, product-led, scalable.                           | —       | polished, product-led, scalable.                           | n/a           | 100.0         | n/a   | —            | —            |
| brand_idea        | video localization at scale.                               | —       | video localization at scale.                               | n/a           | 100.0         | n/a   | —            | —            |
| attributes        | scalable, localized, video-first.                          | —       | scalable, localized, video-first.                          | n/a           | 100.0         | n/a   | —            | —            |
| values            | accessibility, speed, scale.                               | —       | accessibility, speed, scale.                               | n/a           | 100.0         | n/a   | —            | —            |
| mission           | help teams create and localize video at scale.             | —       | help teams create and localize video at scale.             | n/a           | 100.0         | n/a   | —            | —            |
| vision            | video creation becomes faster, more scalable, and more ac… | —       | video creation becomes faster, more scalable, and more ac… | n/a           | 100.0         | n/a   | —            | —            |

## Taxonomy counts

| taxonomy                           | benchmark | scanner | analyst |
| ---------------------------------- | --------- | ------- | ------- |
| attributes_under_extracted         | 1         | 0       | 0       |
| audited_surface_too_narrow         | 1         | 0       | 0       |
| brand_idea_weak_but_not_absent     | 1         | 0       | 0       |
| concept_not_inferred               | 1         | 0       | 0       |
| entity_context_missing             | 0         | 2       | 0       |
| entity_context_not_promoted        | 1         | 0       | 0       |
| false_vision                       | 0         | 1       | 1       |
| feed_or_article_noise              | 1         | 0       | 0       |
| missing_audience                   | 0         | 2       | 1       |
| missing_scanner_scan               | 1         | 0       | 0       |
| overclaim                          | 0         | 18      | 6       |
| parent_entity_not_expanded         | 1         | 0       | 0       |
| product_surface_used_as_full_brand | 1         | 0       | 0       |
| proof_point_as_personality         | 1         | 1       | 1       |
| rhetorical_question_as_purpose     | 1         | 0       | 0       |
| structural_noise_selected          | 1         | 2       | 0       |
| weak_brand_idea                    | 0         | 14      | 8       |
