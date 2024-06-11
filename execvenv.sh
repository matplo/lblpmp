#!/bin/bash

function thisdir()
{
	SOURCE="${BASH_SOURCE[0]}"
	while [ -h "$SOURCE" ]; do # resolve $SOURCE until the file is no longer a symlink
		DIR="$( cd -P "$( dirname "$SOURCE" )" >/dev/null 2>&1 && pwd )"
		SOURCE="$(readlink "$SOURCE")"
		[[ $SOURCE != /* ]] && SOURCE="$DIR/$SOURCE" # if $SOURCE was a relative symlink, we need to resolve it relative to the path where the symlink file was located
	done
	DIR="$( cd -P "$( dirname "$SOURCE" )" >/dev/null 2>&1 && pwd )"
	echo ${DIR}
}
THISD=$(thisdir)

source ${THISD}/bash_util.sh

cd ${THISD}

# The command you want to execute within the virtual environment
# COMMAND="python your_script.py"
COMMAND="$@"

# Extract the first argument
FIRST_ARG="$1"

# Path to your requirements file
REQUIREMENTS="${THISD}/requirements.txt"

# Name of the virtual environment directory
VENV_DIR="${THISD}/venv"

# Unique log file where output and errors will be redirected
LOGFILE="execvenv_$$.log"

# Function to conditionally echo messages based on the VERBOSE environment variable
function conditional_echo() {
    if [[ "$VERBOSE" == "1" ]]; then
        echo "$@"
    fi
}

function install_requirements() {
	# Installing requirements
	if [ -f "$REQUIREMENTS" ]; then
		conditional_echo "Installing requirements from $REQUIREMENTS..." 2>&1 | tee -a $LOGFILE
		if [[ "$VERBOSE" == "1" ]]; then		
			pip install --upgrade pip
			pip install -r $REQUIREMENTS 2>&1 | tee -a $LOGFILE
		else
			pip install -q --upgrade pip
			pip install -q -r $REQUIREMENTS 2>&1 | tee -a $LOGFILE
		fi
	else
		VERBOSE=1
		conditional_echo "Requirements file $REQUIREMENTS does not exist." 2>&1 | tee -a $LOGFILE
		conditional_echo "See $LOGFILE for details." 2>&1 | tee -a $LOGFILE    
		exit 1
	fi
}

# Use this instead of 'echo' for all script messages
conditional_echo "Logging to $LOGFILE" 2>&1 | tee -a $LOGFILE

if [[ ! -z "$VIRTUAL_ENV" ]]; then
	conditional_echo "Looks like we are in an virtual environment." 2>&1 | tee -a $LOGFILE
	if [ "$VIRTUAL_ENV" != "$VENV_DIR" ]; then
		conditional_echo "But not the one we want." 2>&1 | tee -a $LOGFILE
		conditional_echo "Deactivating current virtual environment..." 2>&1 | tee -a $LOGFILE
		if type "deactivate" > /dev/null 2>&1
		then
				deactivate
		fi
		# just to be sure...
		[ ! -z "$VIRTUAL_ENV"] && export VIRTUAL_ENV=""
	fi
fi

# Check if already in a virtual environment by checking the $VIRTUAL_ENV variable
if [[ -z "$VIRTUAL_ENV" ]]
then
    conditional_echo "Not in a virtual environment." 2>&1 | tee -a $LOGFILE

    # Check if the virtual environment directory exists
    if [ ! -d "$VENV_DIR" ]; then
        # Create virtual environment if it does not exist
        conditional_echo "Creating virtual environment using venv..." 2>&1 | tee -a $LOGFILE
        python3 -m venv $VENV_DIR 2>&1 | tee -a $LOGFILE
		source $VENV_DIR/bin/activate
		install_requirements
		if [ "0x$?" != "0x0" ]; then
			conditional_echo "Installing requirements failed." 2>&1 | tee -a $LOGFILE
			exit 1
		fi
		deactivate
    fi

    # Activate the virtual environment
    conditional_echo "Activating virtual environment..." 2>&1 | tee -a $LOGFILE
    source $VENV_DIR/bin/activate
else
    conditional_echo "Already in a virtual environment." 2>&1 | tee -a $LOGFILE
fi

# Execute the command within the virtual environment
conditional_echo "Executing command: $COMMAND" 2>&1 | tee -a $LOGFILE

# Execute the command and capture its exit status
set +e # Temporarily allow commands to fail without exiting the script
# Check if the first argument ends with '.py'
if [[ "$FIRST_ARG" == *.py ]]; then
    $VENV_DIR/bin/python $COMMAND 2>&1 | tee -a $LOGFILE
else
    $COMMAND 2>&1 | tee -a $LOGFILE
fi
exit_status=${PIPESTATUS[0]} # Capture the exit status of the command before tee
set -e # Re-enable immediate exit

if [ $exit_status -eq 0 ]; then
    conditional_echo "Command executed successfully, removing log file." 2>&1 | tee -a $LOGFILE
    rm -f $LOGFILE
	retval=0
else
    VERBOSE=1
    conditional_echo "Command failed with exit code $exit_status, see $LOGFILE for details." 2>&1 | tee -a $LOGFILE
	retval=$exit_status
fi

# Optionally deactivate the virtual environment
if [[ -z "$VIRTUAL_ENV" ]]
then
		conditional_echo "Deactivating virtual environment..." 2>&1 | tee -a $LOGFILE
		deactivate
fi

exit $retval