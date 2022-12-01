import atexit
import datetime
import os
import re
import select
import shutil
import subprocess
from threading import Thread


class ReadTimeout(Exception):
    pass


class SDocTestServer:
    @staticmethod
    def create(path_to_sandbox: str):
        if os.path.isdir(path_to_sandbox):
            shutil.rmtree(path_to_sandbox)
        os.mkdir(path_to_sandbox)

        # _ = GitClient(path_to_git_root=path_to_sandbox, initialize=True)

        test_server = SDocTestServer(
            input_path=path_to_sandbox,
            output_path=None,
        )
        return test_server

    def __init__(self, input_path, output_path):
        assert os.path.isdir(input_path)
        self.path_to_tdoc_folder = input_path
        self.path_to_sandbox = output_path
        self.process = None

    def __del__(self):
        print(f"TestSDocServer: stopping server: {self.process.pid}")
        self.process.kill()

    def run(self):
        args = [
            "python",
            "strictdoc/cli/main.py",
            "server",
            "--no-reload",
            self.path_to_tdoc_folder,
        ]
        if self.path_to_sandbox is not None:
            args.extend(
                [
                    "--output-path",
                    self.path_to_sandbox,
                ]
            )

        temp_file = open("/tmp/sdoctest.out.log", "w")

        # print(f"command: " + " ".join(args))

        process = subprocess.Popen(
            args, stdout=temp_file.fileno(), stderr=subprocess.PIPE, shell=False
        )
        self.process = process

        # A non-blocking read on a subprocess.PIPE in Python
        # https://stackoverflow.com/a/59291466/598057
        os.set_blocking(process.stderr.fileno(), False)

        def exit_handler():
            if process.poll() is None:
                print(f"TestSDocServer: atexit: stopping server: {process.pid}")
                process.kill()

        atexit.register(exit_handler)

        SDocTestServer.receive_expected_response(
            server_process=process,
            expectations=["INFO:     Application startup complete."],
        )
        SDocTestServer.continue_capturing_stderr(server_process=process)

    @staticmethod
    def receive_expected_response(server_process, expectations):
        poll = select.poll()
        poll.register(server_process.stderr, select.POLLIN)
        received_input = []

        start_time = datetime.datetime.now()

        try:
            while len(expectations) > 0:
                check_time = datetime.datetime.now()
                if (check_time - start_time).total_seconds() > 5:
                    raise ReadTimeout()

                if poll.poll(2000):
                    line_bytes = server_process.stderr.readline()
                    while len(expectations) > 0 and line_bytes:
                        line_string = line_bytes.decode("utf-8")
                        current_expectation = expectations[0]
                        received_input.append(line_string)
                        if re.search(
                            current_expectation, f"{line_string.rstrip()}"
                        ):
                            expectations.pop(0)
                        line_bytes = server_process.stderr.readline()
                else:
                    raise ReadTimeout()
        except ReadTimeout:
            print(
                f"---------------------------------------------------------------------"
            )
            print(f"Failed to get an expected response from the server.")
            received_lines = "".join(received_input)
            print(f"Received input:\n{received_lines}")
            exit(1)

        print("TestSDocServer: Server is up and running.")

    @staticmethod
    def enqueue_output(out):
        # This solution also uses Queue but here it is not used.
        # https://stackoverflow.com/a/4896288/598057
        temp_file = open("/tmp/sdoctest.err.log", "wb")

        poll = select.poll()
        poll.register(out, select.POLLIN)

        while True:
            if poll.poll(1000):
                line_bytes = out.readline()
                while line_bytes:
                    temp_file.write(line_bytes)
                    line_bytes = out.readline()
                temp_file.flush()

    @staticmethod
    def continue_capturing_stderr(server_process):
        t = Thread(
            target=SDocTestServer.enqueue_output, args=(server_process.stderr,)
        )
        t.daemon = True  # thread dies with the program
        t.start()

        # # read line without blocking
        # try:
        #     line = q.get_nowait()  # or q.get(timeout=.1)
        # except Empty:
        #     print('no output yet')
        # else:
        #
