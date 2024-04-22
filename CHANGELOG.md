## v1.4.9 (2024-04-22)

### Fix

- fix error msg

## v1.4.8 (2023-09-21)

### Fix

- **exception**: get error message from ErrorDetail

## v1.4.7 (2023-09-21)

### Fix

- **exception**: get error message from ErrorDetail

## v1.4.6 (2023-09-21)

### Fix

- **exception**: get error message from ErrorDetail

## v1.4.5 (2023-09-18)

### Fix

- support NON_FIELD_ERRORS_KEY

## v1.4.4 (2023-09-18)

### Fix

- support NON_FIELD_ERRORS_KEY

## v1.4.3 (2023-09-18)

### Fix

- support NON_FIELD_ERRORS_KEY

## v1.4.2 (2023-09-18)

### Fix

- support NON_FIELD_ERRORS_KEY

## v1.4.1 (2023-09-18)

### Fix

- support NON_FIELD_ERRORS_KEY

## v1.4.0 (2023-09-01)

### Feat

- **fields**: add default db comment

## v1.3.0 (2023-08-21)

### Feat

- support parsing excel and csv files

## v1.2.1 (2023-08-10)

### Fix

- fix bugs when initializing ChoiceArrayField

## v1.2.0 (2023-08-10)

### Feat

- add new field: `ChoiceArrayField`
- add new field: `ChoiceArrayField`

## v1.1.6 (2023-06-21)

### Fix

- fix when set custom through model for

## v1.1.5 (2023-05-16)

### Fix

- support set custom ref_name

## v1.1.4 (2023-03-14)

### Fix

- fix bugs in `AutoFilterBackend`

## v1.1.3 (2023-03-14)

### Fix

- use `setlist` to set query params

## v1.1.2 (2023-03-02)

### Refactor

- strip `[]` in url params

## v1.1.1 (2023-02-28)

### Fix

- fix filter bugs

## v1.1.0 (2023-02-28)

### Feat

- support filter by label field

## v1.0.3 (2023-02-19)

### Refactor

- change the response of `WithoutCountPagination`

## v1.0.2 (2023-02-15)

### Fix

- **renderers**: fix json response

## v1.0.1 (2023-02-08)

### Refactor

- change `max_page_size`

## v1.0.0 (2022-12-22)

### Fix

- **ComplexPKRelatedField**: optimize behavior

## v0.21.3 (2022-12-22)

### Fix

- **ComplexPKRelatedField**: rename  to

## v0.21.2 (2022-12-22)

### Fix

- **ComplexPKRelatedField**: support ManyToMant and ManyToOne relation

## v0.21.1 (2022-12-20)

### Fix

- **serializers**: get  instead of

## v0.21.0 (2022-12-20)

### Feat

- **serializers**: support to set  for

## v0.20.0 (2022-12-07)

### Feat

- add new models with simple status

## v0.19.10 (2022-12-02)

### Fix

- **CreatedByField**: set  to

## v0.19.9 (2022-11-15)

### Fix

- fix function name

### Refactor

- format codes

## v0.19.8 (2022-11-15)

### Refactor

- format codes

## v0.19.7 (2022-11-04)

### Refactor

- remove  cache

## v0.19.6 (2022-11-02)

### Fix

- **serializers**: fix abnormal behavior with

## v0.19.5 (2022-11-02)

### Fix

- **serializers**: fix abnormal behavior with

## v0.19.4 (2022-11-01)

### Fix

- **renderer**: change renderer error message

## v0.19.3 (2022-10-21)

### Fix

- fix that custom method field will be skipped when exporting csv/xlsx

## v0.19.2 (2022-10-19)

### Fix

- fix recursively calling  method

## v0.19.1 (2022-10-19)

### Fix

- ignore KeyError when exporting file

## v0.19.0 (2022-10-19)

### Feat

- pass viewset instance to  and

## v0.18.4 (2022-10-17)

### Fix

- change package ref to url

## v0.18.3 (2022-10-17)

### Fix

- change package ref to url

## v0.18.2 (2022-10-17)

### Fix

- compatible with django 4.0

## v0.18.1 (2022-10-17)

## v0.18.0 (2022-09-27)

### Feat

- add support for setting custom export filename

## v0.17.9 (2022-09-14)

### Fix

- **renderer**: fix some bugs

## v0.17.8 (2022-09-08)

### Fix

- **renderer**: fix some bugs

## v0.17.7 (2022-09-07)

### Fix

- fix rendering erros

## v0.17.6 (2022-09-07)

### Fix

- fix rendering erros

## v0.17.5 (2022-08-31)

### Refactor

- update package dependency

## v0.17.4 (2022-08-31)

### Refactor

- **renderer**: optimize for excel

## v0.17.3 (2022-08-31)

### Fix

- **renderer**: set blank string as default

## v0.17.2 (2022-08-31)

### Fix

- **renderer**: return blank result instead of error page

## v0.17.1 (2022-08-24)

### Fix

- **export**: fix get source attribute error

## v0.17.0 (2022-08-18)

### Feat

- **models**: introduce smart serializer functions to serialize both model and queryset

## v0.16.1 (2022-08-17)

### Fix

- docs return no api  response schema

## v0.16.0 (2022-08-16)

### Feat

- new export mixin
- support define `filterset_base_classes` on viewset.
- **serializer**: support include or exclude fields from serializer
- **serializer**: support dynamicly set fields on serializer

### BREAKING CHANGE

- Uncompatible with previous version!
- remove `get_dynamic_fields` method support

## v0.10.4 (2022-06-21)

## v0.9.0 (2022-04-19)

## v0.1.12 (2022-01-25)
