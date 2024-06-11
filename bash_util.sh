function abspath()
{
  case "${1}" in
    [./]*)
    echo "$(cd ${1%/*}; pwd)/${1##*/}"
    ;;
    *)
    echo "${PWD}/${1}"
    ;;
  esac
}
export -f abspath

function abspath_python_expand()
{
	rv=$(python -c "import os; print(os.path.abspath(os.path.expandvars(\"${1}\")))")
	echo ${rv}
}
export -f abspath_python_expand

function os_linux()
{
	_system=$(uname -a | cut -f 1 -d " ")
	if [ $_system == "Linux" ]; then
		echo "yes"
	else
		echo
	fi
}
export -f os_linux

function os_darwin()
{
	_system=$(uname -a | cut -f 1 -d " ")
	if [ $_system == "Darwin" ]; then
		echo "yes"
	else
		echo
	fi
}
export -f os_darwin

function n_cores()
{
	local _ncores="1"
	[ $(os_darwin) ] && local _ncores=$(system_profiler SPHardwareDataType | grep "Number of Cores" | cut -f 2 -d ":" | sed 's| ||')
	[ $(os_linux) ] && local _ncores=$(lscpu | grep "CPU(s):" | head -n 1 | cut -f 2 -d ":" | sed 's| ||g')
	#[ ${_ncores} -gt "1" ] && retval=$(_ncores-1)
	echo ${_ncores}
}
export -f n_cores

function get_opt()
{
    all_opts="$@"
    # echo "options in function: ${all_opts}"
    opt=${1}
    # echo "checking for [${opt}]"
    #opts=("${all_opts[@]:2}")
    opts=$(echo ${all_opts} | cut -d ' ' -f 2-)
    retval=""
    is_set=""
    # echo ".. in [${opts}]"
    for i in ${opts}
    do
    case $i in
        --${opt}=*)
        retval="${i#*=}"
        shift # past argument=value
        ;;
        --${opt})
        is_set=yes
        shift # past argument with no value
        ;;
        *)
            # unknown option
        ;;
    esac
    done
    if [ -z ${retval} ]; then
        echo ${is_set}
    else
        echo ${retval}
    fi
}
export -f get_opt

need_help=$(get_opt "help" $@)
if [ "x${need_help}" == "xyes" ]; then
    echo "[i] help requested"
fi

function echo_info()
{
	(>&2 echo "[info] $@")
}
export -f echo_info

function echo_warning()
{
	(>&2 echo -e "\033[1;93m$@ \033[0m")
}
export -f echo_warning

function echo_error()
{
	(>&2 echo -e "\033[1;31m$@ \033[0m")
}
export echo_error

function echo_note_red()
{
	(>&2 echo -e "\033[1;31m[note] $@ \033[0m")
}
export echo_note_red

function note_red()
{
	(>&2 echo -e "\033[1;31m[note] $@ \033[0m")
}
export -f note_red

function separator()
{
	echo -e "\033[1;32m$(padding "[ ${1} ]" "-" 50 center) \033[0m"
	## colors at http://misc.flogisoft.com/bash/tip_colors_and_formatting
}
export -f separator

function separator_plain()
{
	echo -e "$(padding "[ ${1} ]" "-" 50 center)"
}
export -f separator_plain

function echo_note()
{
	echo_warning "$(padding "[note] ${@}" "-" 10 left)"
}
export -f echo_note

function note()
{
	echo_warning "$(padding "[note] ${@}" "-" 10 left)"
}
export -f note

function warning()
{
	echo_warning "[warning] $(padding "[${@}] " "-" 40 right)"
}
export -f warning

function error()
{
	echo_error "[error] $(padding "[${@}] " "-" 42 right)"
}
export -f error

function padding ()
{
	CONTENT="${1}";
	PADDING="${2}";
	LENGTH="${3}";
	TRG_EDGE="${4}";
	case "${TRG_EDGE}" in
		left) echo ${CONTENT} | sed -e :a -e 's/^.\{1,'${LENGTH}'\}$/&\'${PADDING}'/;ta'; ;;
		right) echo ${CONTENT} | sed -e :a -e 's/^.\{1,'${LENGTH}'\}$/\'${PADDING}'&/;ta'; ;;
		center) echo ${CONTENT} | sed -e :a -e 's/^.\{1,'${LENGTH}'\}$/'${PADDING}'&'${PADDING}'/;ta'
	esac
	return ${RET__DONE};
}
export -f padding
