/**
 * Find the address-directory row a photo belongs to.
 *
 * The server builds `legal_address`/`simple_address` with
 * COALESCE(manual override, recognised directory). Therefore the displayed
 * legal name is the authoritative binding: a photo whose address was corrected
 * must go to the corrected address, not to the fingerprint HYBRID happened to
 * return. The fingerprint id is only a fallback for photos without names.
 *
 * @param {Array<object>} addresses rows from /v1/addresses (`addr:<id>`)
 * @param {object} photo grid row (address, legal_address, simple_address)
 * @returns {object|null} matching address row
 */
export function addressEntryForPhoto(addresses, photo) {
  const wanted = [photo.legal_address, photo.simple_address]
    .filter(Boolean)
    .map((value) => String(value).trim().toLowerCase())

  for (const field of ['legal_address', 'simple_address', 'name']) {
    if (!wanted.length) break

    const found = (addresses || []).find(
      (item) =>
        item[field]
        && wanted.includes(String(item[field]).trim().toLowerCase()),
    )

    if (found) return found
  }

  if (!photo.address) return null

  return (
    (addresses || []).find(
      (item) =>
        item.address === photo.address
        || (item.fingerprints || []).includes(photo.address),
    ) || null
  )
}
