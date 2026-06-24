# 从 lan_hosts.local.tsv 读取下一行有效主机记录。
# 设置: ip user pass win_path wsl_path_extra ssh_user
read_lan_host_row() {
  local _line _ip _user _pass _win _wsl _ssh
  while IFS= read -r _line || [[ -n "$_line" ]]; do
    [[ -z "$_line" || "$_line" =~ ^[[:space:]]*# ]] && continue
    IFS=$'\t' read -r _ip _user _pass _win _wsl _ssh <<< "$_line"
    [[ -z "${_ip:-}" ]] && continue
    ip="$_ip"
    user="$_user"
    pass="$_pass"
    win_path="$_win"
    wsl_path_extra="${_wsl:-}"
    ssh_user="${_ssh:-$_user}"
    return 0
  done
  return 1
}
