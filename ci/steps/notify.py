import ccc.github
import ci.util
import distutils.util
import glci.notify
import glci.util
import json
import mailutil
import os
from string import Template
import typing
import urllib


def _email_cfg(cicd_cfg: glci.model.CicdCfg):
    ctx = ci.util.ctx()
    cfg_factory = ctx.cfg_factory()
    return cfg_factory.email(cfg_name=cicd_cfg.notify.email_cfg_name)


def _smtp_client(email_cfg):
    return glci.notify.smtp_client(
        host=email_cfg.smtp_host(),
        user=email_cfg.credentials().username(),
        passwd=email_cfg.credentials().passwd(),
)


def send_notification(
    cicd_cfg_name: str,
    giturl: str,
    status_dict_str: str,
    additional_recipients: typing.Sequence[str] = [],
):
    namespace = '$(params.namespace)'
    pipeline_name = '$(params.pipeline_name)'
    pipeline_run = '$(params.pipeline_run_name)'

    repo_dir = '$(params.repo_dir)'

    if distutils.util.strtobool('$(params.disable_notification)'):
        print('Notificcation is disabled, bot sending email')
        return

    status_dict = json.loads(status_dict_str)
    must_send = True in [True for status in status_dict.values() if status != 'Succeeded']

    if not must_send:
        print("All tasks succeded, no notification sent")
        return

    result_table = ""
    for task, status in status_dict.items():
        if status == 'Succeeded':
            status_symbol = '&#9989;'
        elif status == 'Failed':
            status_symbol = '&#10060;'
        else:
            status_symbol = '?'

        result_table += f'<tr><td class="align_left">{task}</td><td>{status_symbol}</td></tr>'

    subject = f'Tekton Pipeline Garden Linux build failure in {pipeline_name}'
    cicd_cfg = glci.util.cicd_cfg(cfg_name=cicd_cfg_name)
    email_cfg = _email_cfg(cicd_cfg=cicd_cfg)

    template_path = os.path.abspath(os.path.join(repo_dir,"ci/templates/email_notification.html"))
    with open(template_path, 'r') as mail_template_file:
        mail_template = mail_template_file.read()

    # read the logo
    logo_path = os.path.abspath(os.path.join(repo_dir,"logo/gardenlinux.svg"))
    with open(logo_path, 'r') as logo_file:
        logo_svg = logo_file.read()

    # replace id and add some attributes
    logo_svg = logo_svg.replace('<svg id="Layer_1"', '<svg id="gl_logo" width="100px"')
    logo_svg = logo_svg.replace('<title>Garden Linux_logo</title>',
        '<title>Garden Linux Logo</title>')

    # fill template parameters:
    html_template = Template(mail_template)
    values = {
        'pipeline': pipeline_name,
        'status_table': result_table,
        'pipeline_run': pipeline_run,
        'namespace': namespace,
        'logo_src': logo_svg,
    }

    # generate mail body
    mail_body = html_template.safe_substitute(values)

    # get recipients from CODEOWNERS:
    parsed_url = urllib.parse.urlparse(giturl)
    github_cfg = ccc.github.github_cfg_for_hostname(parsed_url.hostname)
    github_api = ccc.github.github_api(github_cfg)
    codeowners = mailutil.determine_local_repository_codeowners_recipients(
        github_api=github_api,
        src_dirs=(repo_dir,),
    )

    # eliminate duplicates by converting it to a set:
    recipients = {r for r in codeowners}
    recipients |= set(additional_recipients)
    if len(recipients) == 0:
        print('Mail not sent, could not find any recipient.')
        return

    print(f'Send notification to following recipients: {recipients}')
    mail_msg = glci.notify.mk_html_mail_body(
        text=mail_body,
        recipients=recipients,
        subject=subject,
        sender=email_cfg.sender_name(),
    )

    # for debugging generate a local file
    # with open('email_out.html', 'w') as file:
    #     file.write(mail_body)

    mail_client = _smtp_client(email_cfg=email_cfg)
    mail_client.send_message(msg=mail_msg)