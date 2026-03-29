export function formatDate(value?: string | null) {
  if (!value) return '未记录'
  return new Date(value).toLocaleString('zh-CN')
}
